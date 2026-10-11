"""Documented Lemmy v3 native posts/comments; no account or media downloads."""
import transport as t
from entities import edge

def records(data,sid,base):
 rows=[]
 for view in data.get('posts',[])+data.get('comments',[]):
  iscomment='comment' in view;obj=view.get('comment') if iscomment else view.get('post');obj=obj or {};nid=obj.get('id')
  if nid is None:continue
  ns='comment' if iscomment else 'post';post=view.get('post') or {};creator=view.get('creator') or {};community=view.get('community') or {};deleted=bool(obj.get('deleted') or obj.get('removed'));body=obj.get('content') if iscomment else obj.get('body');body=body or '';title=post.get('name')
  state='tombstone_native_return' if deleted else 'complete_native_text' if body else 'native_title_only_text' if title and not iscomment else 'bodyless_native_entity'
  edges=[];root=str(obj.get('post_id') or post.get('id') or nid);parent=None;parentns=None
  if iscomment:
   edges.append(edge('root',root,'post'));path=(obj.get('path') or '').split('.')
   if len(path)>2:parent=path[-2];parentns='comment'
   elif path and len(path)==2:parent=root;parentns='post'
   if parent:edges.append(edge('reply',parent,parentns))
  if obj.get('url'):edges.append(edge('link',None,url=obj['url']))
  attachments=[]
  for field in ['thumbnail_url','url','embed_video_url']:
   if obj.get(field):attachments.append({'type':'native_'+field,'url':obj[field],'source_native_field':'post.'+field})
  rows.append(dict(source_id=sid,native_namespace=ns,native_post_id=str(nid),source_url=obj.get('ap_id') or base+('/comment/' if iscomment else '/post/')+str(nid),native_unit='tombstone' if deleted else 'forum_reply' if iscomment else 'link_only_post' if not body and obj.get('url') else 'forum_post',native_created_at=obj.get('published'),native_edited_at=obj.get('updated'),body_original=body or (title if not iscomment else '') or '',body_format='plain',content_state=state,content_license='no_open_content_grant_verified',license_basis='Documented public API and bounded local-retention scope; software and sidebar licences are not applied to posts',thread_id=root,reply_to_post_id=parent,parent_namespace=parentns,author_id=str(creator.get('id')) if creator.get('id') is not None else None,author_role='unknown',flags={'native_deleted':obj.get('deleted'),'native_removed':obj.get('removed'),'native_local':obj.get('local'),'native_locked':obj.get('locked'),'native_nsfw':obj.get('nsfw'),'stored_original_field':('comment.content' if iscomment else 'post.body') if body else 'post.name/title_only_no_body' if title else None,'source_community_local':community.get('local'),'native_language_id':obj.get('language_id')},native_fields={'lemmy.post':{k:v for k,v in post.items() if k!='body'},'lemmy.comment':{k:v for k,v in obj.items() if k!='content'} if iscomment else None,'lemmy.creator':{k:creator.get(k) for k in ['id','actor_id','local','bot_account','banned','deleted']},'lemmy.community':{k:community.get(k) for k in ['id','name','title','actor_id','local','deleted','removed']},'lemmy.counts':view.get('counts')},edges=edges,attachments=attachments))
  if iscomment and post.get('id') is not None:
   parents=records({'posts':[{'post':post,'creator':{'id':post.get('creator_id')},'community':community}]},sid,base)
   for parent in parents:parent['flags']['returned_as_lemmy_comment_root_context']=True
   rows.extend(parents)
 return rows
