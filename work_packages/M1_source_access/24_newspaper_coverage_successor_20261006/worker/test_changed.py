import datetime as dt,json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import core,frontier

class Scheduling(unittest.TestCase):
    def test_round_robin_opportunity_no_transfer(self):
        strata=core.SCOPE['strata'];qs={s:[s+'1',s+'2'] for s in strata}
        self.assertEqual(frontier.alternate(qs),[s+'1' for s in strata]+[s+'2' for s in strata])
        qs[strata[0]]=[];result=frontier.alternate(qs)
        self.assertEqual(result.count(strata[-1]+'1'),1)
    def test_missing_month_native_order_not_length(self):
        rows=[dict(stratum='US',publication_date=d,native_id=n) for d,n in [('2007-04-01','dense'),('1990-03-04','first'),('1990-03-01','second'),('1988-02-01','earliest')]]
        selected,remaining=frontier.select(rows,{('US','2007-04')})
        self.assertEqual([r['native_id'] for r in selected],['earliest','first']);self.assertEqual(len(remaining),2)
    def test_fixed_endpoint_and_native_url(self):
        self.assertTrue(core.eligible('2026-09-21'));self.assertFalse(core.eligible('2026-09-22'));self.assertFalse(core.eligible('1987-12-31'));self.assertFalse(core.eligible('1990-02-30'))
        self.assertEqual(frontier.date_url('https://newspaper/1995/03/02/story'),'1995-03-02')
        self.assertIsNone(frontier.date_url('https://newspaper/2026/10/02/story'))

class Resources(unittest.TestCase):
    def test_allocation_exhaustion_is_not_disk_full(self):
        with patch('core.cumulative',return_value=core.SCOPE['media_lifetime_cap_bytes']-100),patch('core.shutil.disk_usage',return_value=type('D',(),{'free':30*1024**3})()):
            b=core.preflight(200,0);self.assertFalse(b['passed']);self.assertEqual(b['limiting_constraint'],'cumulative_media_allocation')
    def test_physical_floor_zero_inherited_reserve(self):
        with patch('core.cumulative',return_value=0),patch('core.shutil.disk_usage',return_value=type('D',(),{'free':core.SCOPE['physical_floor_bytes']+100})()):
            b=core.preflight(0,0);self.assertFalse(b['passed']);self.assertEqual(b['original_combined_reserve_bytes'],0);self.assertEqual(b['limiting_constraint'],'physical_floor_or_lease')
    def test_retained_copies_and_recovery_are_reserved(self):
        b=core.preflight(1024,3072);self.assertEqual(b['recovery_allowance_bytes'],48*1024**2);self.assertEqual(b['derived_cap_bytes'],3072)

class Staging(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.own=Path(self.tmp.name);self.lock=self.own/'shared.lock'
        self.a=patch('core.OWN',self.own);self.a.start();self.b=patch('core.LOCK',self.lock);self.b.start();self.c=patch('core.material_check',return_value={'passed':True});self.c.start()
        self.record=dict(unit_id='article1',source_id='fixture',stratum='US',publication_date='1990-02-06',title='Native article',unit_kind='mapped_article',raw_sha256='a'*64,body_sha256='b'*64)
    def tearDown(self):self.c.stop();self.b.stop();self.a.stop();self.tmp.cleanup()
    def test_interruption_rolls_back_unit_version_cursor(self):
        with self.assertRaises(RuntimeError):core.stage(self.record,interrupt=True)
        con=sqlite3.connect(self.own/'staging.sqlite3')
        for table in ['units','versions','cursors']:self.assertEqual(con.execute('SELECT count(*) FROM '+table).fetchone()[0],0)
        con.close()
    def test_restart_idempotence_and_new_version(self):
        self.assertEqual(core.stage(self.record),1);self.assertEqual(core.stage(self.record),0)
        self.assertEqual(core.stage({**self.record,'body_sha256':'c'*64}),1)
    def test_date_conflict_cannot_reassign_parent(self):
        core.stage(self.record)
        with self.assertRaises(ValueError):core.stage({**self.record,'publication_date':'1991-02-06'})
    def test_frozen_target_cannot_be_replaced(self):
        t=core.freeze_target('fixture','US','https://example.com/1990/02/06/article','article','native fixture',['example.com'],'1990-02')
        self.assertEqual(t,core.freeze_target('fixture','US',t['url'],'article','native fixture',['example.com'],'1990-02'))
        with self.assertRaises(RuntimeError):core.freeze_target('fixture','US',t['url'],'article','new frame',['example.com'],'1990-02')

if __name__=='__main__':unittest.main(verbosity=2)
