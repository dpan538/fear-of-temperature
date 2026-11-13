# Complete Current Query Matrix

Frozen v3.15 semantic definitions: 10 parents, 24 named sub-parents, 350 base-term memberships, 343 direct children and 295 grouped children. Total: 638 children and 988 memberships (985 distinct literal terms). Query associations are not emotion gold labels.

The complete machine-readable counterpart is [current.json](../../../config/search/current.json). Search dimensions and family weights are in [profiles.json](../../../config/search/profiles.json) and [weights.json](../../../config/search/weights.json).

## Effort and scope

Somatic/daily and psychological/cultural effort weights are 1.60, ecology/memory 1.50, irony/metaphor 1.35 and broad exploration 1.00. Explicit saved job families and weights take precedence over parent defaults. Year, city and genre hints are optional discovery dimensions, not universal conjunctions. Mild, medical, mixed, indirect, metaphorical and policy/scientist/alarmism-backlash texts remain in scope. The preferred 1,000–2,500-token range has no hard length gate.

| Parent | Base | Direct children | Grouped children | Sub-parents | Default family | Weight |
|---|---:|---:|---:|---:|---|---:|
| Warming & changing seasons | 31 | 19 | 0 | 0 | broad_forum_exploration | 1.00 |
| Acute heat & temperature extremes | 55 | 21 | 0 | 0 | somatic_daily_impact | 1.60 |
| Somatic & daily-life experience | 54 | 39 | 12 | 1 | somatic_daily_impact | 1.60 |
| Irritability & anger | 22 | 7 | 18 | 2 | psychological_cultural_response | 1.60 |
| Fear, anxiety & anticipation | 23 | 21 | 201 | 15 | psychological_cultural_response | 1.60 |
| Exhaustion & aversion | 27 | 16 | 44 | 4 | psychological_cultural_response | 1.60 |
| Housing, costs & inequality | 48 | 50 | 8 | 1 | somatic_daily_impact | 1.60 |
| Individual & household coping | 53 | 39 | 0 | 0 | somatic_daily_impact | 1.60 |
| Policy, science & collective action | 20 | 63 | 12 | 1 | psychological_cultural_response | 1.60 |
| Weather, ecology & fire-risk context | 17 | 68 | 0 | 0 | ecological_grief_memory | 1.50 |

## Warming & changing seasons

Parent ID: `warming_seasons`.

### Standalone base terms

- `rising temperature`
- `rising temperatures`
- `warming`
- `global warming`
- `climate change`
- `hotter summers`
- `hotter summer`
- `warmer summers`
- `warmer summer`
- `warmer winters`
- `warm winter`
- `getting hotter`
- `getting warmer`
- `hotter than`
- `warmer than`
- `unseasonably warm`
- `unseasonal warmth`
- `changing seasons`
- `climate crisis`
- `climate emergency`
- `hotter and hotter`
- `warmer and warmer`
- `summers are longer`
- `longer summers`
- `earlier spring`
- `late autumn`
- `warming planet`
- `warming world`
- `climate breakdown`
- `climate disruption`
- `climate grief`

### Canonical children

| Child ID | Expression | Sub-parent |
|---|---|---|
| `warming_seasons.child.10db699812` | climate | Direct child |
| `warming_seasons.child.2819193247` | climatic | Direct child |
| `warming_seasons.child.059a062e34` | climatechange | Direct child |
| `warming_seasons.child.3314a29864` | globalwarming | Direct child |
| `warming_seasons.child.079d631659` | warming climate | Direct child |
| `warming_seasons.child.0091a533bd` | warmest | Direct child |
| `warming_seasons.child.6015993a38` | hotter | Direct child |
| `warming_seasons.child.097092286f` | hottest | Direct child |
| `warming_seasons.child.e83664255c` | summer | Direct child |
| `warming_seasons.child.e84e17ec88` | summers | Direct child |
| `warming_seasons.child.5a2a0ed9aa` | heat | Direct child |
| `warming_seasons.child.7f5d1618e7` | hot | Direct child |
| `warming_seasons.child.0f0aa408c1` | warm | Direct child |
| `warming_seasons.child.ac6c362bf0` | wet season | Direct child |
| `warming_seasons.child.000af82570` | dry season | Direct child |
| `warming_seasons.child.a5b37d4691` | build up | Direct child |
| `warming_seasons.child.34c1abddad` | build-up | Direct child |
| `warming_seasons.child.853e902e9d` | midsummer | Direct child |
| `warming_seasons.child.b6d1b7c637` | unseasonal | Direct child |

## Acute heat & temperature extremes

Parent ID: `acute_heat`.

### Standalone base terms

- `heatwave`
- `heatwaves`
- `heat wave`
- `heat waves`
- `extreme heat`
- `hot weather`
- `hot day`
- `hot days`
- `hot night`
- `hot nights`
- `hot spell`
- `heat dome`
- `scorcher`
- `scorching`
- `sweltering`
- `stinking hot`
- `bloody hot`
- `so hot`
- `too hot`
- `boiling hot`
- `baking hot`
- `oppressive heat`
- `summer heat`
- `summer sun`
- `unbearably hot`
- `unbearable heat`
- `stifling heat`
- `heat stress`
- `heat stroke`
- `heatstroke`
- `record temperatures`
- `record temperature`
- `record heat`
- `heatwave warning`
- `heat wave warning`
- `heat alert`
- `severe heatwave`
- `extreme heatwave`
- `hot as hell`
- `I'm melting`
- `I am melting`
- `we're melting`
- `muggy`
- `humid`
- `humidity`
- `sticky heat`
- `sticky night`
- `sticky nights`
- `stinking bloody hot`
- `roasting hot`
- `cooking in the heat`
- `forty degrees`
- `40 degree heat`
- `a scorcher`
- `hotter than hell`

### Canonical children

| Child ID | Expression | Sub-parent |
|---|---|---|
| `acute_heat.child.f83381ff9b` | blistering | Direct child |
| `acute_heat.child.9b78665395` | roasting | Direct child |
| `acute_heat.child.df690b4bb7` | boiling | Direct child |
| `acute_heat.child.aa463bda3b` | melting | Direct child |
| `acute_heat.child.b74ccffb3a` | stifling | Direct child |
| `acute_heat.child.d93c68d7cf` | scorching heat | Direct child |
| `acute_heat.child.56bbbb0a1a` | baking | Direct child |
| `acute_heat.child.fd42598d81` | sticky weather | Direct child |
| `acute_heat.child.c417d427d6` | parched | Direct child |
| `acute_heat.child.5d22b21276` | desiccated | Direct child |
| `acute_heat.child.b399e87283` | swelter | Direct child |
| `acute_heat.child.1c7fbf976f` | sweltered | Direct child |
| `acute_heat.child.6875673927` | searing | Direct child |
| `acute_heat.child.76eac2d48d` | scorched | Direct child |
| `acute_heat.child.8246a95f95` | sun-drenched | Direct child |
| `acute_heat.child.c8429a58dc` | sizzling | Direct child |
| `acute_heat.child.bce8d813a5` | dry heat | Direct child |
| `acute_heat.child.74612423f1` | torrid | Direct child |
| `acute_heat.child.38fb15f005` | sultry | Direct child |
| `acute_heat.child.e9b0f44761` | heat haze | Direct child |
| `acute_heat.child.18addc0892` | prolonged heat | Direct child |

## Somatic & daily-life experience

Parent ID: `body_daily_life`.

### Standalone base terms

- `sweat`
- `sweaty`
- `sweating`
- `dehydrated`
- `dehydration`
- `exhausted`
- `exhaustion`
- `fatigue`
- `tired`
- `can't sleep`
- `couldn't sleep`
- `cannot sleep`
- `sleepless`
- `sleep`
- `insomnia`
- `tossing and turning`
- `working outside`
- `outdoor work`
- `commute`
- `commuting`
- `walking`
- `hiking`
- `bushwalking`
- `cycling`
- `garden`
- `gardening`
- `plants`
- `school`
- `children`
- `pregnant`
- `headache`
- `brain fog`
- `heat rash`
- `prickly heat`
- `heat exhaustion`
- `night sweats`
- `overheating`
- `overheated`
- `sleepless nights`
- `sweating buckets`
- `sweating like`
- `sweating through`
- `sunburn`
- `sunburnt`
- `sunburned`
- `heat fatigue`
- `too hot to work`
- `too hot to walk`
- `too hot to sleep`
- `heat exposure`
- `heat intolerance`
- `sticky`
- `clammy`
- `sunscreen`

### Canonical children

| Child ID | Expression | Sub-parent |
|---|---|---|
| `body_daily_life.child.f275a34960` | sweats | Direct child |
| `body_daily_life.child.eb18e991e3` | sweated | Direct child |
| `body_daily_life.child.546f04bb7a` | sleeping | Direct child |
| `body_daily_life.child.1953403821` | sleeplessness | Direct child |
| `body_daily_life.child.3ae3348877` | choking | Direct child |
| `body_daily_life.child.f07d989f1a` | choke | Direct child |
| `body_daily_life.child.866ab33b84` | cough | Direct child |
| `body_daily_life.child.73413e3826` | coughing | Direct child |
| `body_daily_life.child.50d4cb584b` | breathing | Direct child |
| `body_daily_life.child.816a9b880a` | breathless | Direct child |
| `body_daily_life.child.5841108008` | unbreathable | Direct child |
| `body_daily_life.child.695b2ea90e` | asthma | Direct child |
| `body_daily_life.child.3b5d7cbf57` | fatigued | Direct child |
| `body_daily_life.child.b800c84eeb` | heat-related | Direct child |
| `body_daily_life.child.c7a3fafc39` | sleep deprivation | Direct child |
| `v3_3_198` | food insecurity | Direct child |
| `v3_3_199` | outdoor workers | Direct child |
| `v3_4_208` | rural communities | Direct child |
| `v3_4_213` | road closures | Direct child |
| `v3_4_215` | remote communities | Direct child |
| `v3_4_222` | out bush | Direct child |
| `v3_4_228` | remote community | Direct child |
| `v3_5_233` | wellbeing | Direct child |
| `v3_5_235` | mental health | Direct child |
| `v3_5_236` | connection to country | Direct child |
| `v3_5_237` | sense of belonging | Direct child |
| `v3_5_240` | mental wellbeing | Direct child |
| `body_daily_life.child.bb45339560` | wilting | Direct child |
| `body_daily_life.child.16257ab1d2` | soil moisture | Direct child |
| `body_daily_life.child.c7e9b3a93c` | restless night | Direct child |
| `body_daily_life.child.70b18d5bda` | thirst | Direct child |
| `body_daily_life.child.03f3ef3063` | thirsty | Direct child |
| `body_daily_life.child.409310a012` | perspiration | Direct child |
| `body_daily_life.child.3a59b5d106` | restlessness | Direct child |
| `body_daily_life.child.517d445705` | kinship | Direct child |
| `body_daily_life.child.0b80c840b3` | retirement | Direct child |
| `body_daily_life.child.0790b890d0` | olden days | Direct child |
| `body_daily_life.child.6c0d09328e` | young at heart | Direct child |
| `body_daily_life.child.54b0326342` | memory loss | Direct child |
| `body_daily_life.child.continuum.a80086330f70` | kept awake by the heat | continuum_embodied_feedback |
| `body_daily_life.child.continuum.07b404fb5db8` | awake all night in the heat | continuum_embodied_feedback |
| `body_daily_life.child.continuum.1ba0d96ef7aa` | aircon on all night | continuum_embodied_feedback |
| `body_daily_life.child.continuum.8c8d65ace9c6` | air conditioning all night | continuum_embodied_feedback |
| `body_daily_life.child.continuum.d768a3b2f283` | could not sleep in the heat | continuum_embodied_feedback |
| `body_daily_life.child.continuum.2fc817e4e56c` | can't cool down | continuum_embodied_feedback |
| `body_daily_life.child.continuum.acdaf86e99f8` | cannot cool down | continuum_embodied_feedback |
| `body_daily_life.child.continuum.3fbfc2330cf0` | unable to cool down | continuum_embodied_feedback |
| `body_daily_life.child.continuum.fe2c7ee18949` | hot flushes | continuum_embodied_feedback |
| `body_daily_life.child.continuum.b5f51ebb5389` | heat makes me dizzy | continuum_embodied_feedback |
| `body_daily_life.child.continuum.37e5f675e149` | too exhausted to do anything | continuum_embodied_feedback |
| `body_daily_life.child.continuum.a741673b75e8` | sweating through the sheets | continuum_embodied_feedback |

### continuum_embodied_feedback

Canonical assignments: **12**. Declared discovery expressions: **12**.

`kept awake by the heat`; `awake all night in the heat`; `aircon on all night`; `air conditioning all night`; `could not sleep in the heat`; `can't cool down`; `cannot cool down`; `unable to cool down`; `hot flushes`; `heat makes me dizzy`; `too exhausted to do anything`; `sweating through the sheets`.

## Irritability & anger

Parent ID: `heat_irritability_anger`.

### Standalone base terms

- `heat rage`
- `summer rage`
- `make my blood boil`
- `driving me crazy`
- `driving me insane`
- `irritable`
- `irritability`
- `losing my temper`
- `zero patience`
- `short fuse`
- `snapping at`
- `agitated`
- `rage`
- `angry`
- `angry at the heat`
- `grumpy`
- `cranky`
- `ratty`
- `bad temper`
- `short tempered`
- `short-tempered`
- `heat makes me angry`

### Canonical children

| Child ID | Expression | Sub-parent |
|---|---|---|
| `heat_irritability_anger.child.d4cc56aa47` | anger | Direct child |
| `heat_irritability_anger.child.72e850d110` | annoyed | Direct child |
| `heat_irritability_anger.child.92e93e7e81` | annoying | Direct child |
| `heat_irritability_anger.child.6afb642998` | frustrated | Direct child |
| `heat_irritability_anger.child.1748ba31e2` | frustration | Direct child |
| `heat_irritability_anger.child.ab8e1efe40` | furious | Direct child |
| `heat_irritability_anger.child.7d00bbc6d8` | shame on you | Direct child |
| `heat_irritability_anger.child.a0816c4df6` | climate anger | heat_climate_anger |
| `heat_irritability_anger.child.caa275b9d1` | climate rage | heat_climate_anger |
| `heat_irritability_anger.child.c9888e5463` | eco-anger | heat_climate_anger |
| `heat_irritability_anger.child.4e70ad5f05` | eco anger | heat_climate_anger |
| `heat_irritability_anger.child.f87e8a4048` | irritable in the heat | heat_climate_anger |
| `heat_irritability_anger.child.71d80c388f` | heat makes me irritable | heat_climate_anger |
| `heat_irritability_anger.child.74dba093a8` | angry about climate change | heat_climate_anger |
| `heat_irritability_anger.child.42f4a5ac83` | climate frustration | heat_climate_anger |
| `heat_irritability_anger.child.fearcolloquial.d48ec2b32e` | pissed off | anger_colloquial_and_heat_metaphors |
| `heat_irritability_anger.child.fearcolloquial.f441831bba` | shits me | anger_colloquial_and_heat_metaphors |
| `heat_irritability_anger.child.fearcolloquial.c9ad81411f` | drives me mad | anger_colloquial_and_heat_metaphors |
| `heat_irritability_anger.child.fearcolloquial.20f9827a79` | driving me mad | anger_colloquial_and_heat_metaphors |
| `heat_irritability_anger.child.fearcolloquial.b7d29da976` | boiling with rage | anger_colloquial_and_heat_metaphors |
| `heat_irritability_anger.child.fearcolloquial.f9279a44ee` | makes my blood boil | anger_colloquial_and_heat_metaphors |
| `heat_irritability_anger.child.fearcolloquial.137cd574b4` | my blood boils | anger_colloquial_and_heat_metaphors |
| `heat_irritability_anger.child.fearcolloquial.c210dd566f` | seeing red | anger_colloquial_and_heat_metaphors |
| `heat_irritability_anger.child.fearcolloquial.a91259d8c3` | spitting chips | anger_colloquial_and_heat_metaphors |
| `heat_irritability_anger.child.fearcolloquial.b00655272e` | cracking the shits | anger_colloquial_and_heat_metaphors |

### heat_climate_anger

Canonical assignments: **8**. Declared discovery expressions: **8**.

`climate anger`; `climate rage`; `eco-anger`; `eco anger`; `irritable in the heat`; `heat makes me irritable`; `angry about climate change`; `climate frustration`.

### anger_colloquial_and_heat_metaphors

Canonical assignments: **10**. Declared discovery expressions: **10**.

`pissed off`; `shits me`; `drives me mad`; `driving me mad`; `boiling with rage`; `makes my blood boil`; `my blood boils`; `seeing red`; `spitting chips`; `cracking the shits`.

## Fear, anxiety & anticipation

Parent ID: `climate_anxiety_anticipation`.

### Standalone base terms

- `dreading`
- `dread`
- `anxiety`
- `anxious`
- `fear`
- `scared`
- `terrified`
- `panic`
- `horrified`
- `worried`
- `worry`
- `climate anxiety`
- `eco-anxiety`
- `eco anxiety`
- `ecological anxiety`
- `climate grief`
- `eco grief`
- `solastalgia`
- `dreading summer`
- `scared of summer`
- `fear of heat`
- `heat anxiety`
- `weather anxiety`

### Canonical children

| Child ID | Expression | Sub-parent |
|---|---|---|
| `climate_anxiety_anticipation.child.8e506e203c` | fears | Direct child |
| `climate_anxiety_anticipation.child.331b049e72` | fearful | Direct child |
| `climate_anxiety_anticipation.child.6f804d1d5b` | worries | Direct child |
| `climate_anxiety_anticipation.child.10fbdf9d5e` | worrying | Direct child |
| `climate_anxiety_anticipation.child.1d0dbd158c` | frightened | Direct child |
| `climate_anxiety_anticipation.child.8bd72e7d46` | concerned | Direct child |
| `climate_anxiety_anticipation.child.fcfc5fe39f` | concerns | Direct child |
| `climate_anxiety_anticipation.child.ad12f62c45` | trauma | Direct child |
| `climate_anxiety_anticipation.child.36ed555122` | traumatised | Direct child |
| `climate_anxiety_anticipation.child.1e402e1118` | traumatized | Direct child |
| `climate_anxiety_anticipation.child.6d997a0a13` | devastated | Direct child |
| `climate_anxiety_anticipation.child.268bf8ce9e` | devastation | Direct child |
| `climate_anxiety_anticipation.child.669ff3caa4` | climate dread | Direct child |
| `climate_anxiety_anticipation.child.3af3e24667` | ecological collapse | Direct child |
| `climate_anxiety_anticipation.child.2d5f8e4d77` | ecological grief | Direct child |
| `climate_anxiety_anticipation.child.32ceacc06e` | vulnerability | Direct child |
| `climate_anxiety_anticipation.child.45c1bb8a95` | on edge | Direct child |
| `climate_anxiety_anticipation.child.80e24a3fb2` | unsettled | Direct child |
| `climate_anxiety_anticipation.child.8e21d97ec8` | intergenerational trauma | Direct child |
| `climate_anxiety_anticipation.child.33147abbc2` | survivor guilt | Direct child |
| `climate_anxiety_anticipation.child.9019f8058b` | uncertainty | Direct child |
| `climate_anxiety_anticipation.child.aa28704ccb` | dread summer | summer_anticipatory_fear |
| `climate_anxiety_anticipation.child.76b187f676` | dread the summer | summer_anticipatory_fear |
| `climate_anxiety_anticipation.child.0450440308` | afraid of summer | summer_anticipatory_fear |
| `climate_anxiety_anticipation.child.5d7a637162` | fear of summer | summer_anticipatory_fear |
| `climate_anxiety_anticipation.child.17628fa154` | scared of the heat | summer_anticipatory_fear |
| `climate_anxiety_anticipation.child.311ff0cfa5` | afraid of the heat | summer_anticipatory_fear |
| `climate_anxiety_anticipation.child.1b8f96fe9f` | fear of rising temperatures | summer_anticipatory_fear |
| `climate_anxiety_anticipation.child.6ad7aabf28` | summer anxiety | summer_anticipatory_fear |
| `climate_anxiety_anticipation.child.63bc49631c` | heatwave anxiety | heatwave_panic |
| `climate_anxiety_anticipation.child.ccf3c28af4` | heatwave fear | heatwave_panic |
| `climate_anxiety_anticipation.child.6aa5fa5eef` | heatwave panic | heatwave_panic |
| `climate_anxiety_anticipation.child.e75e188a42` | heat panic | heatwave_panic |
| `climate_anxiety_anticipation.child.ef77f6d0a5` | terrified of the heat | heatwave_panic |
| `climate_anxiety_anticipation.child.c0ae43ed07` | fear of extreme heat | heatwave_panic |
| `climate_anxiety_anticipation.child.3679672442` | panic about the heat | heatwave_panic |
| `climate_anxiety_anticipation.child.a2b7d15221` | dreading the heat | heatwave_panic |
| `climate_anxiety_anticipation.child.0eba14e87c` | climate fear | future_climate_dread |
| `climate_anxiety_anticipation.child.336396709a` | climate fears | future_climate_dread |
| `climate_anxiety_anticipation.child.3781107cab` | climate despair | future_climate_dread |
| `climate_anxiety_anticipation.child.a7467a5121` | climate distress | future_climate_dread |
| `climate_anxiety_anticipation.child.b29857bbd5` | climate hopelessness | future_climate_dread |
| `climate_anxiety_anticipation.child.334a9bec93` | worried about climate change | future_climate_dread |
| `climate_anxiety_anticipation.child.a5010a23af` | scared about climate change | future_climate_dread |
| `climate_anxiety_anticipation.child.dfd33fcd4b` | fear for the future | future_climate_dread |
| `climate_anxiety_anticipation.child.3ea8f31d2f` | climate sorrow | ecological_loss_grief |
| `climate_anxiety_anticipation.child.3e4d25da37` | ecological mourning | ecological_loss_grief |
| `climate_anxiety_anticipation.child.f9cd8adbe7` | environmental grief | ecological_loss_grief |
| `climate_anxiety_anticipation.child.6d47505b8b` | environmental distress | ecological_loss_grief |
| `climate_anxiety_anticipation.child.bb801b9b11` | grieving for the planet | ecological_loss_grief |
| `climate_anxiety_anticipation.child.10c7af1e8c` | grief for country | ecological_loss_grief |
| `climate_anxiety_anticipation.child.98f442f66d` | ecological despair | ecological_loss_grief |
| `climate_anxiety_anticipation.child.635bc55723` | eco-despair | ecological_loss_grief |
| `climate_anxiety_anticipation.child.4d574c3397` | learned to fear the heat | learned_shared_fear |
| `climate_anxiety_anticipation.child.e39f17077f` | learning to fear the heat | learned_shared_fear |
| `climate_anxiety_anticipation.child.c6fb9057f1` | grew up fearing summer | learned_shared_fear |
| `climate_anxiety_anticipation.child.db9a6b0b89` | collective climate anxiety | learned_shared_fear |
| `climate_anxiety_anticipation.child.7443f51419` | shared climate grief | learned_shared_fear |
| `climate_anxiety_anticipation.child.f72e345ebd` | intergenerational climate anxiety | learned_shared_fear |
| `climate_anxiety_anticipation.child.a4288e45d6` | climate emotions | learned_shared_fear |
| `climate_anxiety_anticipation.child.b6db7b5091` | climate feelings | learned_shared_fear |
| `climate_anxiety_anticipation.child.55b7d5320d` | bushfire anxiety | fire_season_memory |
| `climate_anxiety_anticipation.child.b1b64cfab5` | bushfire fear | fire_season_memory |
| `climate_anxiety_anticipation.child.3497ea4f81` | bushfire trauma | fire_season_memory |
| `climate_anxiety_anticipation.child.1540d505ad` | fire season anxiety | fire_season_memory |
| `climate_anxiety_anticipation.child.2d7d39e15d` | dreading fire season | fire_season_memory |
| `climate_anxiety_anticipation.child.5094aa0d74` | afraid of bushfires | fire_season_memory |
| `climate_anxiety_anticipation.child.a12363c981` | bushfire grief | fire_season_memory |
| `climate_anxiety_anticipation.child.d578fcaa48` | fear of another black summer | fire_season_memory |
| `climate_anxiety_anticipation.child.fearlayer.585f5d7241` | afraid | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.8f20046b88` | fright | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.a47798ff88` | frightening | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.0fa5319172` | frightful | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.7ff3de39c8` | terrifying | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.778419bb50` | terror | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.018ea3f347` | horror | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.c8e5857e96` | horrifying | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.7a07348885` | fearfully | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.da288b384a` | dreadful | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.22d3caa669` | dreaded | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.32059a0771` | uneasy | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.483d88a57d` | unease | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.197d3e1d14` | nervous | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.931bc07aea` | nervously | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.6abb61efc0` | nervousness | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.fc35f3e809` | apprehensive | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.58865e1913` | apprehension | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.98ad38845b` | trepidation | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.a8aac303c8` | petrified | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.e38733a927` | unnerved | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.a10afe6833` | unnerving | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.ca50e5372b` | alarmed | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.038067ba94` | alarming | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.fb9eae9054` | intimidated | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.eaa788cff6` | intimidating | fear_ordinary_variants |
| `climate_anxiety_anticipation.child.fearlayer.b9ebf94e03` | heart in my mouth | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.f713432ebf` | heart sank | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.001d662980` | my stomach dropped | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.9e9f1b20fa` | stomach in knots | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.db6177ac83` | knot in my stomach | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.192728159d` | butterflies in my stomach | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.f72a118d9f` | blood ran cold | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.529a27e60c` | cold sweat | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.12becbe78c` | cold sweats | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.b69f544315` | scared stiff | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.98f27bef3d` | scared witless | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.1609c3d19d` | scared to death | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.1e0e1a8594` | worried sick | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.4392ec8c45` | sick with worry | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.13f831a8d2` | on tenterhooks | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.85ca75acc1` | walking on eggshells | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.7a4a4196b7` | waiting for the other shoe to drop | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.3014f081c9` | ticking time bomb | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.1e0f6d61c4` | ticking timebomb | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.a777ffc75a` | looming threat | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.1e4153093a` | dark cloud hanging over | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.343aa50423` | drowning in worry | fear_indirect_idioms |
| `climate_anxiety_anticipation.child.fearlayer.21e731a160` | learned fear | fear_learned_shared_expression |
| `climate_anxiety_anticipation.child.fearlayer.4767d72819` | learned to fear | fear_learned_shared_expression |
| `climate_anxiety_anticipation.child.fearlayer.1ae3eea654` | learning to fear | fear_learned_shared_expression |
| `climate_anxiety_anticipation.child.fearlayer.4f7575956d` | taught to fear | fear_learned_shared_expression |
| `climate_anxiety_anticipation.child.fearlayer.87421f4ace` | grew up afraid | fear_learned_shared_expression |
| `climate_anxiety_anticipation.child.fearlayer.fd412c3b87` | grew up fearing | fear_learned_shared_expression |
| `climate_anxiety_anticipation.child.fearlayer.0a9b0fd916` | shared fear | fear_learned_shared_expression |
| `climate_anxiety_anticipation.child.fearlayer.c8ba3904cf` | collective fear | fear_learned_shared_expression |
| `climate_anxiety_anticipation.child.fearlayer.5c46f4f447` | intergenerational fear | fear_learned_shared_expression |
| `climate_anxiety_anticipation.child.fearlayer.93789b18e7` | fear passed down | fear_learned_shared_expression |
| `climate_anxiety_anticipation.child.fearlayer.64789a5642` | cultural fear | fear_learned_shared_expression |
| `climate_anxiety_anticipation.child.fearvariants.5105904627` | scary | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.ad4c527da5` | scare | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.6ddd123fbe` | scares | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.b83a76f598` | scaring | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.1516ec95e5` | creepy | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.f1557900df` | creepiness | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.73740548d2` | spooky | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.ab9e099756` | eerie | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.4d73dda619` | hair-raising | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.55b05fc6a6` | phobia | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.b80d4497a4` | phobias | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.00e4b7308b` | phobic | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.5c52840591` | paranoia | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.7bc0ee8330` | paranoid | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.e33ad38576` | foreboding | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.6dc9142eee` | traumatic | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.c110d8a9c9` | harrowing | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.e82ab91619` | terrorised | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.7975a11def` | terrorized | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.785347d101` | fearmongering | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.c5182f07a5` | fear-mongering | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.96043763a8` | fear mongering | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.71b56acbaf` | scaremongering | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.3de4847e17` | scare-mongering | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.231559bcae` | scare mongering | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.f2c8ca0e1d` | scare campaign | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.09b00aad8f` | scare campaigns | fear_ordinary_cultural_variants |
| `climate_anxiety_anticipation.child.fearvariants.8807e0f837` | freaking out | fear_ordinary_indirect_idioms |
| `climate_anxiety_anticipation.child.fearvariants.45f89efca9` | freaked out | fear_ordinary_indirect_idioms |
| `climate_anxiety_anticipation.child.fearvariants.bf80f73647` | freaks me out | fear_ordinary_indirect_idioms |
| `climate_anxiety_anticipation.child.fearvariants.6d362ce4a2` | freak me out | fear_ordinary_indirect_idioms |
| `climate_anxiety_anticipation.child.fearvariants.0bcef93e59` | on pins and needles | fear_ordinary_indirect_idioms |
| `climate_anxiety_anticipation.child.fearvariants.870d1a32c6` | heart in my throat | fear_ordinary_indirect_idioms |
| `climate_anxiety_anticipation.child.fearvariants.fe5a6ab7a9` | hair stood on end | fear_ordinary_indirect_idioms |
| `climate_anxiety_anticipation.child.fearvariants.e38d1d1576` | shivers down my spine | fear_ordinary_indirect_idioms |
| `climate_anxiety_anticipation.child.fearvariants.9c78c4fdc6` | shiver down my spine | fear_ordinary_indirect_idioms |
| `climate_anxiety_anticipation.child.fearvariants.b3d6ee0d03` | sends chills down my spine | fear_ordinary_indirect_idioms |
| `climate_anxiety_anticipation.child.fearvariants.d76e924d16` | gives me the creeps | fear_ordinary_indirect_idioms |
| `climate_anxiety_anticipation.child.fearvariants.0e22e4bde3` | give me the creeps | fear_ordinary_indirect_idioms |
| `climate_anxiety_anticipation.child.fearvariants.1a8d8ca520` | cold feet | fear_ordinary_indirect_idioms |
| `climate_anxiety_anticipation.child.fearvariants.306d180a18` | nerve-racking | fear_ordinary_indirect_idioms |
| `climate_anxiety_anticipation.child.fearvariants.eaa9340b42` | nerve-wracking | fear_ordinary_indirect_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.e5795842da` | eek | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.300812157b` | eeek | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.c8de9074a8` | yikes | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.9d93813685` | shit scared | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.0e39fa5129` | shitscared | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.d10f6f4196` | scared shitless | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.b6d62f447a` | scared out of my wits | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.fd976b2734` | scared out of your wits | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.cbd13b204d` | jumped out of my skin | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.9bd28a3c83` | jump out of my skin | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.0dab4c7651` | shaking like a leaf | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.ecfe23fc05` | shaking in my boots | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.51ab37c5e2` | quaking in my boots | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.64b05b04f6` | rabbit in the headlights | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.a4bd9031b0` | deer in the headlights | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.89e5bcaef3` | frozen with fear | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.690e990d97` | paralysed with fear | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.69d45b8456` | paralyzed with fear | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.dde8949839` | nervous wreck | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.fearcolloquial.0f111f183f` | bundle of nerves | fear_colloquial_interjections_and_embodied_idioms |
| `climate_anxiety_anticipation.child.continuum.ad296536bba0` | absolutely terrified | continuum_fear_anxiety |
| `climate_anxiety_anticipation.child.continuum.d3b47a9e2f9d` | utterly terrified | continuum_fear_anxiety |
| `climate_anxiety_anticipation.child.continuum.e5dfc475b531` | scared out of my mind | continuum_fear_anxiety |
| `climate_anxiety_anticipation.child.continuum.ebf562017899` | terrified for my children | continuum_fear_anxiety |
| `climate_anxiety_anticipation.child.continuum.3b7a0c9fb232` | dread the forecast | continuum_fear_anxiety |
| `climate_anxiety_anticipation.child.continuum.6ae47b34f7b6` | panic at the forecast | continuum_fear_anxiety |
| `climate_anxiety_anticipation.child.continuum.3fcfb56474d4` | anxiety about the future | continuum_fear_anxiety |
| `climate_anxiety_anticipation.child.continuum.c24fd1f65aab` | no future for our children | continuum_fear_anxiety |
| `climate_anxiety_anticipation.child.continuum.07af87533840` | overcome with dread | continuum_fear_anxiety |
| `climate_anxiety_anticipation.child.continuum.940c048321bb` | a sense of impending doom | continuum_fear_anxiety |
| `climate_anxiety_anticipation.child.continuum.7e1e2b031d99` | climate terror | continuum_fear_anxiety |
| `climate_anxiety_anticipation.child.continuum.c8452cea9606` | existential dread | continuum_fear_anxiety |
| `climate_anxiety_anticipation.child.continuum.de53ee60f8f5` | leaves burnt to a crisp | continuum_ecological_metaphor |
| `climate_anxiety_anticipation.child.continuum.de2c9d55538c` | trees dying in the heat | continuum_ecological_metaphor |
| `climate_anxiety_anticipation.child.continuum.8fb1d2f53e40` | garden is dying | continuum_ecological_metaphor |
| `climate_anxiety_anticipation.child.continuum.404704a8f5a3` | country is crying | continuum_ecological_metaphor |
| `climate_anxiety_anticipation.child.continuum.7d536e5339db` | mourning the landscape | continuum_ecological_metaphor |
| `climate_anxiety_anticipation.child.continuum.cb1e9a461d1e` | burnt leaves | continuum_ecological_metaphor |
| `climate_anxiety_anticipation.child.continuum.76cfc8439e46` | scorched garden | continuum_ecological_metaphor |
| `climate_anxiety_anticipation.child.continuum.b5197a38a9b7` | the land is grieving | continuum_ecological_metaphor |
| `climate_anxiety_anticipation.child.continuum.a4946e3b0465` | home feels unfamiliar | continuum_ecological_metaphor |
| `climate_anxiety_anticipation.child.continuum.02246367118c` | summer feels like a threat | continuum_ecological_metaphor |
| `climate_anxiety_anticipation.child.continuum.68923052dd89` | living in an oven | continuum_ecological_metaphor |
| `climate_anxiety_anticipation.child.continuum.3f5afb2dd01d` | cooked alive | continuum_ecological_metaphor |
| `climate_anxiety_anticipation.child.continuum.3e158cf0337b` | learnt to fear | continuum_cultural_learning |
| `climate_anxiety_anticipation.child.continuum.a94e83d2256b` | raised to fear | continuum_cultural_learning |
| `climate_anxiety_anticipation.child.continuum.d46270370bc2` | my parents warned me | continuum_cultural_learning |
| `climate_anxiety_anticipation.child.continuum.f22b9380b4e3` | we were taught | continuum_cultural_learning |
| `climate_anxiety_anticipation.child.continuum.500c26c3727b` | we have always feared | continuum_cultural_learning |
| `climate_anxiety_anticipation.child.continuum.ee8e3452c102` | inherited fear | continuum_cultural_learning |
| `climate_anxiety_anticipation.child.continuum.2c0c690fa995` | cultural memory of fire | continuum_cultural_learning |
| `climate_anxiety_anticipation.child.continuum.8f030a5b1246` | remembering the old summers | continuum_cultural_learning |

### summer_anticipatory_fear

Canonical assignments: **8**. Declared discovery expressions: **8**.

`dread summer`; `dread the summer`; `afraid of summer`; `fear of summer`; `scared of the heat`; `afraid of the heat`; `fear of rising temperatures`; `summer anxiety`.

### heatwave_panic

Canonical assignments: **8**. Declared discovery expressions: **8**.

`heatwave anxiety`; `heatwave fear`; `heatwave panic`; `heat panic`; `terrified of the heat`; `fear of extreme heat`; `panic about the heat`; `dreading the heat`.

### future_climate_dread

Canonical assignments: **8**. Declared discovery expressions: **8**.

`climate fear`; `climate fears`; `climate despair`; `climate distress`; `climate hopelessness`; `worried about climate change`; `scared about climate change`; `fear for the future`.

### ecological_loss_grief

Canonical assignments: **8**. Declared discovery expressions: **8**.

`climate sorrow`; `ecological mourning`; `environmental grief`; `environmental distress`; `grieving for the planet`; `grief for country`; `ecological despair`; `eco-despair`.

### learned_shared_fear

Canonical assignments: **8**. Declared discovery expressions: **8**.

`learned to fear the heat`; `learning to fear the heat`; `grew up fearing summer`; `collective climate anxiety`; `shared climate grief`; `intergenerational climate anxiety`; `climate emotions`; `climate feelings`.

### fire_season_memory

Canonical assignments: **8**. Declared discovery expressions: **8**.

`bushfire anxiety`; `bushfire fear`; `bushfire trauma`; `fire season anxiety`; `dreading fire season`; `afraid of bushfires`; `bushfire grief`; `fear of another black summer`.

### fear_ordinary_variants

Canonical assignments: **26**. Declared discovery expressions: **26**.

`afraid`; `fright`; `frightening`; `frightful`; `terrifying`; `terror`; `horror`; `horrifying`; `fearfully`; `dreadful`; `dreaded`; `uneasy`; `unease`; `nervous`; `nervously`; `nervousness`; `apprehensive`; `apprehension`; `trepidation`; `petrified`; `unnerved`; `unnerving`; `alarmed`; `alarming`; `intimidated`; `intimidating`.

### fear_indirect_idioms

Canonical assignments: **22**. Declared discovery expressions: **22**.

`heart in my mouth`; `heart sank`; `my stomach dropped`; `stomach in knots`; `knot in my stomach`; `butterflies in my stomach`; `blood ran cold`; `cold sweat`; `cold sweats`; `scared stiff`; `scared witless`; `scared to death`; `worried sick`; `sick with worry`; `on tenterhooks`; `walking on eggshells`; `waiting for the other shoe to drop`; `ticking time bomb`; `ticking timebomb`; `looming threat`; `dark cloud hanging over`; `drowning in worry`.

### fear_learned_shared_expression

Canonical assignments: **11**. Declared discovery expressions: **11**.

`learned fear`; `learned to fear`; `learning to fear`; `taught to fear`; `grew up afraid`; `grew up fearing`; `shared fear`; `collective fear`; `intergenerational fear`; `fear passed down`; `cultural fear`.

### fear_ordinary_cultural_variants

Canonical assignments: **27**. Declared discovery expressions: **27**.

`scary`; `scare`; `scares`; `scaring`; `creepy`; `creepiness`; `spooky`; `eerie`; `hair-raising`; `phobia`; `phobias`; `phobic`; `paranoia`; `paranoid`; `foreboding`; `traumatic`; `harrowing`; `terrorised`; `terrorized`; `fearmongering`; `fear-mongering`; `fear mongering`; `scaremongering`; `scare-mongering`; `scare mongering`; `scare campaign`; `scare campaigns`.

### fear_ordinary_indirect_idioms

Canonical assignments: **15**. Declared discovery expressions: **15**.

`freaking out`; `freaked out`; `freaks me out`; `freak me out`; `on pins and needles`; `heart in my throat`; `hair stood on end`; `shivers down my spine`; `shiver down my spine`; `sends chills down my spine`; `gives me the creeps`; `give me the creeps`; `cold feet`; `nerve-racking`; `nerve-wracking`.

### fear_colloquial_interjections_and_embodied_idioms

Canonical assignments: **20**. Declared discovery expressions: **20**.

`eek`; `eeek`; `yikes`; `shit scared`; `shitscared`; `scared shitless`; `scared out of my wits`; `scared out of your wits`; `jumped out of my skin`; `jump out of my skin`; `shaking like a leaf`; `shaking in my boots`; `quaking in my boots`; `rabbit in the headlights`; `deer in the headlights`; `frozen with fear`; `paralysed with fear`; `paralyzed with fear`; `nervous wreck`; `bundle of nerves`.

### continuum_fear_anxiety

Canonical assignments: **12**. Declared discovery expressions: **12**.

`absolutely terrified`; `utterly terrified`; `scared out of my mind`; `terrified for my children`; `dread the forecast`; `panic at the forecast`; `anxiety about the future`; `no future for our children`; `overcome with dread`; `a sense of impending doom`; `climate terror`; `existential dread`.

### continuum_ecological_metaphor

Canonical assignments: **12**. Declared discovery expressions: **12**.

`leaves burnt to a crisp`; `trees dying in the heat`; `garden is dying`; `country is crying`; `mourning the landscape`; `burnt leaves`; `scorched garden`; `the land is grieving`; `home feels unfamiliar`; `summer feels like a threat`; `living in an oven`; `cooked alive`.

### continuum_cultural_learning

Canonical assignments: **8**. Declared discovery expressions: **12**.

`learnt to fear`; `learned to fear`; `taught to fear`; `grew up afraid`; `raised to fear`; `my parents warned me`; `we were taught`; `we have always feared`; `fear passed down`; `inherited fear`; `cultural memory of fire`; `remembering the old summers`.

## Exhaustion & aversion

Parent ID: `exhaustion_aversion`.

### Standalone base terms

- `miserable`
- `depressing`
- `depression`
- `overwhelmed`
- `can't cope`
- `cannot cope`
- `can't take this anymore`
- `breaking point`
- `hopeless`
- `mental drain`
- `mentally drained`
- `hate`
- `despise`
- `can't stand`
- `suffocating`
- `hellish`
- `pure torture`
- `nightmare`
- `stressed`
- `uncomfortable`
- `fed up`
- `over it`
- `summer depression`
- `hate the heat`
- `hate summer`
- `depressing heat`
- `exhausted from the heat`

### Canonical children

| Child ID | Expression | Sub-parent |
|---|---|---|
| `exhaustion_aversion.child.22c90970f5` | depressed | Direct child |
| `exhaustion_aversion.child.4943e60532` | overwhelming | Direct child |
| `exhaustion_aversion.child.b15c961913` | suffocate | Direct child |
| `exhaustion_aversion.child.2f9e3d0f18` | suffocation | Direct child |
| `exhaustion_aversion.child.736a9444e8` | struggling | Direct child |
| `exhaustion_aversion.child.72b268f826` | struggle | Direct child |
| `exhaustion_aversion.child.7170b2782d` | stressing | Direct child |
| `exhaustion_aversion.child.a3260757ea` | stressed out | Direct child |
| `exhaustion_aversion.child.a4f4e73f0d` | burnout | Direct child |
| `exhaustion_aversion.child.41f09a211a` | burnt out | Direct child |
| `exhaustion_aversion.child.c63741be7b` | burned out | Direct child |
| `exhaustion_aversion.child.78f8a6ac06` | soporific | Direct child |
| `exhaustion_aversion.child.4bd886b613` | disconnection | Direct child |
| `exhaustion_aversion.child.d88ed6a0ee` | alienation | Direct child |
| `exhaustion_aversion.child.137d1f2a7f` | despairing | Direct child |
| `exhaustion_aversion.child.02efaf4e24` | bereft | Direct child |
| `exhaustion_aversion.child.c1c98c1ac9` | hate hot weather | heat_aversion |
| `exhaustion_aversion.child.e2103f5858` | hate this heat | heat_aversion |
| `exhaustion_aversion.child.7c64b5e88e` | hate the hot weather | heat_aversion |
| `exhaustion_aversion.child.7786c84c22` | cannot stand the heat | heat_aversion |
| `exhaustion_aversion.child.896712f76c` | can't stand the heat | heat_aversion |
| `exhaustion_aversion.child.b74742f368` | sick of the heat | heat_aversion |
| `exhaustion_aversion.child.f64b211aae` | fed up with the heat | heat_aversion |
| `exhaustion_aversion.child.269907838f` | dread hot weather | heat_aversion |
| `exhaustion_aversion.child.ee4c823500` | heat misery | heat_entrapment_exhaustion |
| `exhaustion_aversion.child.4d6d837686` | miserable in the heat | heat_entrapment_exhaustion |
| `exhaustion_aversion.child.8ac367d8c8` | heat makes me miserable | heat_entrapment_exhaustion |
| `exhaustion_aversion.child.44d1204d4a` | overwhelmed by the heat | heat_entrapment_exhaustion |
| `exhaustion_aversion.child.5540be9a92` | trapped by the heat | heat_entrapment_exhaustion |
| `exhaustion_aversion.child.1ebd7df4f9` | no escape from the heat | heat_entrapment_exhaustion |
| `exhaustion_aversion.child.9f109b5481` | summer dread | heat_entrapment_exhaustion |
| `exhaustion_aversion.child.c745d05ab3` | summer blues | heat_entrapment_exhaustion |
| `exhaustion_aversion.child.fearcolloquial.f4eb9a5a37` | black dog | distress_colloquial_and_cultural_metaphors |
| `exhaustion_aversion.child.fearcolloquial.888775ee37` | black dogs | distress_colloquial_and_cultural_metaphors |
| `exhaustion_aversion.child.fearcolloquial.bf58cea427` | at breaking point | distress_colloquial_and_cultural_metaphors |
| `exhaustion_aversion.child.fearcolloquial.69d317ff09` | emotional wreck | distress_colloquial_and_cultural_metaphors |
| `exhaustion_aversion.child.fearcolloquial.268afe814f` | dying inside | distress_colloquial_and_cultural_metaphors |
| `exhaustion_aversion.child.fearcolloquial.15985f21a7` | at my wit's end | distress_colloquial_and_cultural_metaphors |
| `exhaustion_aversion.child.fearcolloquial.9fcaf6e54f` | at my wits end | distress_colloquial_and_cultural_metaphors |
| `exhaustion_aversion.child.fearcolloquial.472ead9eb0` | at the end of my tether | distress_colloquial_and_cultural_metaphors |
| `exhaustion_aversion.child.fearcolloquial.7ece97c630` | can't take it anymore | distress_colloquial_and_cultural_metaphors |
| `exhaustion_aversion.child.fearcolloquial.f7bbab10f8` | cannot take it anymore | distress_colloquial_and_cultural_metaphors |
| `exhaustion_aversion.child.fearcolloquial.f343304815` | sick and tired | distress_colloquial_and_cultural_metaphors |
| `exhaustion_aversion.child.fearcolloquial.81e085f72a` | gutted | distress_colloquial_and_cultural_metaphors |
| `exhaustion_aversion.child.fearcolloquial.f69ca1f4bf` | heartbroken | distress_colloquial_and_cultural_metaphors |
| `exhaustion_aversion.child.fearcolloquial.eb2a863f86` | heartbreaking | distress_colloquial_and_cultural_metaphors |
| `exhaustion_aversion.child.fearcolloquial.da4697f878` | hopelessness | distress_colloquial_and_cultural_metaphors |
| `exhaustion_aversion.child.fearcolloquial.87bf4aa8b6` | helplessness | distress_colloquial_and_cultural_metaphors |
| `exhaustion_aversion.child.continuum.210d59860fde` | a bit too hot | continuum_mild_discomfort |
| `exhaustion_aversion.child.continuum.7a89ac6fd0e4` | slightly too hot | continuum_mild_discomfort |
| `exhaustion_aversion.child.continuum.2205e1b44094` | this heat is annoying | continuum_mild_discomfort |
| `exhaustion_aversion.child.continuum.4585937aec39` | sick of sweating | continuum_mild_discomfort |
| `exhaustion_aversion.child.continuum.47b6804d5af3` | getting sick of this heat | continuum_mild_discomfort |
| `exhaustion_aversion.child.continuum.36c65f8f2fd0` | another hot night | continuum_mild_discomfort |
| `exhaustion_aversion.child.continuum.d9f5554cf205` | more heat again | continuum_mild_discomfort |
| `exhaustion_aversion.child.continuum.0486807f67cb` | heat is getting to me | continuum_mild_discomfort |
| `exhaustion_aversion.child.continuum.12c2d3a291d2` | too warm for comfort | continuum_mild_discomfort |
| `exhaustion_aversion.child.continuum.ab7fdd7525f8` | a little worried | continuum_mild_discomfort |
| `exhaustion_aversion.child.continuum.f66eac74fc06` | not looking forward to summer | continuum_mild_discomfort |
| `exhaustion_aversion.child.continuum.7eaca1196d07` | fed up with summer | continuum_mild_discomfort |

### heat_aversion

Canonical assignments: **8**. Declared discovery expressions: **8**.

`hate hot weather`; `hate this heat`; `hate the hot weather`; `cannot stand the heat`; `can't stand the heat`; `sick of the heat`; `fed up with the heat`; `dread hot weather`.

### heat_entrapment_exhaustion

Canonical assignments: **8**. Declared discovery expressions: **8**.

`heat misery`; `miserable in the heat`; `heat makes me miserable`; `overwhelmed by the heat`; `trapped by the heat`; `no escape from the heat`; `summer dread`; `summer blues`.

### distress_colloquial_and_cultural_metaphors

Canonical assignments: **16**. Declared discovery expressions: **16**.

`black dog`; `black dogs`; `at breaking point`; `emotional wreck`; `dying inside`; `at my wit's end`; `at my wits end`; `at the end of my tether`; `can't take it anymore`; `cannot take it anymore`; `sick and tired`; `gutted`; `heartbroken`; `heartbreaking`; `hopelessness`; `helplessness`.

### continuum_mild_discomfort

Canonical assignments: **12**. Declared discovery expressions: **12**.

`a bit too hot`; `slightly too hot`; `this heat is annoying`; `sick of sweating`; `getting sick of this heat`; `another hot night`; `more heat again`; `heat is getting to me`; `too warm for comfort`; `a little worried`; `not looking forward to summer`; `fed up with summer`.

## Housing, costs & inequality

Parent ID: `homes_costs_inequality`.

### Standalone base terms

- `house`
- `home`
- `bedroom`
- `apartment`
- `flat`
- `rental`
- `renting`
- `renter`
- `tenant`
- `landlord`
- `electricity`
- `energy bill`
- `power bill`
- `bills`
- `afford`
- `cost`
- `expensive`
- `poverty`
- `homeless`
- `inequality`
- `inequity`
- `elderly`
- `neighbour`
- `neighbor`
- `community`
- `family`
- `housing`
- `heat island`
- `double glazing`
- `double glazed`
- `single glazing`
- `west facing`
- `west-facing`
- `uninsulated`
- `poor insulation`
- `heat trap`
- `hot box`
- `hotbox`
- `thermal comfort`
- `energy poverty`
- `high electricity bill`
- `high power bill`
- `bill shock`
- `rental minimum standards`
- `top floor`
- `top-floor`
- `heat inequity`
- `urban heat`

### Canonical children

| Child ID | Expression | Sub-parent |
|---|---|---|
| `homes_costs_inequality.child.a2f6728145` | housing shortage | Direct child |
| `homes_costs_inequality.child.de352f3925` | housing crisis | Direct child |
| `homes_costs_inequality.child.526aeeff59` | rents | Direct child |
| `homes_costs_inequality.child.955c0ff445` | rented | Direct child |
| `homes_costs_inequality.child.0373280943` | renters | Direct child |
| `homes_costs_inequality.child.c39f46ab6d` | energy costs | Direct child |
| `homes_costs_inequality.child.84ddddcde8` | food prices | Direct child |
| `homes_costs_inequality.child.47f2691263` | grocery prices | Direct child |
| `homes_costs_inequality.child.1f4cc28039` | vegetable prices | Direct child |
| `homes_costs_inequality.child.78aad30559` | cost of living | Direct child |
| `homes_costs_inequality.child.567ec64635` | food bill | Direct child |
| `homes_costs_inequality.child.53371c061d` | water bill | Direct child |
| `homes_costs_inequality.child.efc4dfd44a` | water shortage | Direct child |
| `homes_costs_inequality.child.84173fd057` | water restrictions | Direct child |
| `homes_costs_inequality.child.34da525a0f` | ran out of water | Direct child |
| `homes_costs_inequality.child.3d38ebbe03` | homes destroyed | Direct child |
| `homes_costs_inequality.child.39066c4a47` | lost my home | Direct child |
| `homes_costs_inequality.child.85163d4513` | lost our home | Direct child |
| `homes_costs_inequality.child.ad7c52bed3` | power outage | Direct child |
| `homes_costs_inequality.child.28780a3cd2` | blackout | Direct child |
| `homes_costs_inequality.child.0d9d29a677` | blackouts | Direct child |
| `homes_costs_inequality.child.ad31db60e3` | power cuts | Direct child |
| `homes_costs_inequality.child.b784d80a1d` | student housing | Direct child |
| `homes_costs_inequality.child.77b76165a5` | rental crisis | Direct child |
| `homes_costs_inequality.child.a0fccbbc1a` | housing insecurity | Direct child |
| `v3_3_189` | public housing | Direct child |
| `v3_3_190` | social housing | Direct child |
| `v3_3_191` | housing affordability | Direct child |
| `v3_3_197` | social isolation | Direct child |
| `v3_3_202` | rental stress | Direct child |
| `v3_4_210` | food supply | Direct child |
| `v3_4_217` | water security | Direct child |
| `v3_4_223` | remote housing | Direct child |
| `v3_4_229` | overcrowded housing | Direct child |
| `v3_5_232` | rental affordability | Direct child |
| `v3_5_238` | disadvantaged communities | Direct child |
| `v3_5_239` | cost-of-living | Direct child |
| `v3_5_246` | food relief | Direct child |
| `v3_5_247` | rough sleeping | Direct child |
| `v3_5_248` | housing stress | Direct child |
| `v3_5_249` | housing waitlist | Direct child |
| `homes_costs_inequality.child.dcd2d24e4a` | displacement | Direct child |
| `homes_costs_inequality.child.4cdc24a5a5` | precarity | Direct child |
| `homes_costs_inequality.child.3be2ab9ced` | sense of place | Direct child |
| `homes_costs_inequality.child.e4dcb24f65` | belonging | Direct child |
| `homes_costs_inequality.child.0d5322c22c` | dislocation | Direct child |
| `homes_costs_inequality.child.663dbb15a9` | cultural safety | Direct child |
| `homes_costs_inequality.child.e97b6fa430` | insecure housing | Direct child |
| `homes_costs_inequality.child.fe312219d9` | downsizing | Direct child |
| `homes_costs_inequality.child.192a6db174` | ageism | Direct child |
| `homes_costs_inequality.child.ab755ee2a8` | afraid to turn on the air conditioning | unequal_heat_distress |
| `homes_costs_inequality.child.b75fd7ed2a` | cannot afford to keep cool | unequal_heat_distress |
| `homes_costs_inequality.child.7dbfe6de91` | can't afford to keep cool | unequal_heat_distress |
| `homes_costs_inequality.child.f73fbe1b8a` | trapped in a hot house | unequal_heat_distress |
| `homes_costs_inequality.child.c0acfce203` | sweltering at home | unequal_heat_distress |
| `homes_costs_inequality.child.72ad62a2e1` | heat vulnerability | unequal_heat_distress |
| `homes_costs_inequality.child.301dbae733` | cooling poverty | unequal_heat_distress |
| `homes_costs_inequality.child.8df156d837` | heat injustice | unequal_heat_distress |

### unequal_heat_distress

Canonical assignments: **8**. Declared discovery expressions: **8**.

`afraid to turn on the air conditioning`; `cannot afford to keep cool`; `can't afford to keep cool`; `trapped in a hot house`; `sweltering at home`; `heat vulnerability`; `cooling poverty`; `heat injustice`.

## Individual & household coping

Parent ID: `individual_household_coping`.

### Standalone base terms

- `aircon`
- `air con`
- `air conditioning`
- `air-conditioning`
- `air conditioner`
- `cooling`
- `cool down`
- `staying cool`
- `keeping cool`
- `keep cool`
- `fan`
- `fans`
- `shade`
- `shading`
- `insulation`
- `insulate`
- `curtains`
- `blinds`
- `ventilation`
- `evaporative`
- `swimming`
- `pool`
- `water`
- `adapt`
- `adaptation`
- `resilience`
- `resilient`
- `portable AC`
- `portable air conditioner`
- `evaporative cooler`
- `evaporative cooling`
- `ceiling fan`
- `ceiling fans`
- `reverse cycle`
- `split system`
- `split-system`
- `double glazing`
- `double glazed`
- `solar panel`
- `solar panels`
- `solar energy`
- `solar power`
- `cool roof`
- `cool roofs`
- `cross ventilation`
- `cross-ventilation`
- `verandah`
- `veranda`
- `shade cloth`
- `shadecloth`
- `breeze`
- `sea breeze`
- `Fremantle Doctor`

### Canonical children

| Child ID | Expression | Sub-parent |
|---|---|---|
| `individual_household_coping.child.cb8c02ecad` | wfh | Direct child |
| `individual_household_coping.child.b9d5868a1f` | work from home | Direct child |
| `individual_household_coping.child.84d702456f` | working from home | Direct child |
| `individual_household_coping.child.34ed41d1e7` | stay indoors | Direct child |
| `individual_household_coping.child.a3a17f0b9b` | staying indoors | Direct child |
| `individual_household_coping.child.029e956803` | stay inside | Direct child |
| `individual_household_coping.child.6bdcea0ba7` | staying inside | Direct child |
| `individual_household_coping.child.012d6a08f0` | evacuation | Direct child |
| `individual_household_coping.child.2342909968` | evacuate | Direct child |
| `individual_household_coping.child.0110c494eb` | evacuated | Direct child |
| `individual_household_coping.child.23565920a0` | evacuating | Direct child |
| `individual_household_coping.child.cd96b5def4` | shelter | Direct child |
| `individual_household_coping.child.8cb7a8a0a8` | refuge | Direct child |
| `individual_household_coping.child.824ef78741` | rescue | Direct child |
| `individual_household_coping.child.ea6a344e27` | relief | Direct child |
| `individual_household_coping.child.2ec45b88c6` | cooler | Direct child |
| `individual_household_coping.child.13d4f3a6e3` | coolers | Direct child |
| `individual_household_coping.child.0b94070b8d` | cooling off | Direct child |
| `individual_household_coping.child.17416af7cf` | keep hydrated | Direct child |
| `individual_household_coping.child.c249729916` | drinking water | Direct child |
| `individual_household_coping.child.2bfbc118ab` | solar | Direct child |
| `individual_household_coping.child.3c95f956f6` | renewableenergy | Direct child |
| `individual_household_coping.child.2d9ec79ae9` | cleanenergy | Direct child |
| `individual_household_coping.child.ca24cad8d4` | wicking beds | Direct child |
| `individual_household_coping.child.fa1f310b31` | wicking bed | Direct child |
| `individual_household_coping.child.68a25502cc` | rainwater tank | Direct child |
| `individual_household_coping.child.ece81c9616` | self-sufficiency | Direct child |
| `individual_household_coping.child.ebdb7fa014` | permaculture | Direct child |
| `individual_household_coping.child.936c4e99a7` | reticulation | Direct child |
| `individual_household_coping.child.71f7e8b4f8` | self sufficiency | Direct child |
| `v3_4_219` | air conditioned | Direct child |
| `v3_4_224` | water tank | Direct child |
| `v3_4_226` | water tanks | Direct child |
| `v3_5_245` | community kitchen | Direct child |
| `v3_5_250` | rainwater harvesting | Direct child |
| `v3_5_252` | drought tolerant | Direct child |
| `v3_5_253` | waterwise | Direct child |
| `individual_household_coping.child.50c9c96e63` | waterhole | Direct child |
| `individual_household_coping.child.d87834662a` | rainwater | Direct child |

## Policy, science & collective action

Parent ID: `systemic_policy_collective_action`.

### Standalone base terms

- `heat plan`
- `heat policy`
- `climate policy`
- `climate action`
- `climate adaptation`
- `carbon tax`
- `emissions`
- `protest`
- `petition`
- `activism`
- `climate justice`
- `environmental justice`
- `climate strike`
- `school strike`
- `fossil fuel`
- `fossil fuels`
- `net zero`
- `heat refuge`
- `cooling centre`
- `cooling center`

### Canonical children

| Child ID | Expression | Sub-parent |
|---|---|---|
| `systemic_policy_collective_action.child.28d79d50ff` | carbon | Direct child |
| `systemic_policy_collective_action.child.ad41e95765` | carbon credits | Direct child |
| `systemic_policy_collective_action.child.4185cec3c2` | carbon emissions | Direct child |
| `systemic_policy_collective_action.child.6d114c95fb` | coal | Direct child |
| `systemic_policy_collective_action.child.0a149844a7` | logging | Direct child |
| `systemic_policy_collective_action.child.d1d2451ac1` | deforestation | Direct child |
| `systemic_policy_collective_action.child.ba5285161b` | environment | Direct child |
| `systemic_policy_collective_action.child.4cb948126b` | environmental | Direct child |
| `systemic_policy_collective_action.child.18f0350e28` | renewable | Direct child |
| `systemic_policy_collective_action.child.8aa3cf9fc1` | renewables | Direct child |
| `systemic_policy_collective_action.child.6750cb68b3` | renewable energy | Direct child |
| `systemic_policy_collective_action.child.9504a1c199` | climate summit | Direct child |
| `systemic_policy_collective_action.child.ba74a13786` | climate disaster | Direct child |
| `systemic_policy_collective_action.child.f0b7378d3e` | climate apocalypse | Direct child |
| `systemic_policy_collective_action.child.bd1028594e` | climate denial | Direct child |
| `systemic_policy_collective_action.child.9be2224887` | climate misinformation | Direct child |
| `systemic_policy_collective_action.child.51b7ed3d5f` | protests | Direct child |
| `systemic_policy_collective_action.child.995341958f` | petitions | Direct child |
| `systemic_policy_collective_action.child.8fcccd18b6` | adani | Direct child |
| `systemic_policy_collective_action.child.6461b1efd9` | climatecrisis | Direct child |
| `systemic_policy_collective_action.child.43029a964b` | sustainability | Direct child |
| `systemic_policy_collective_action.child.19577d1214` | stopadani | Direct child |
| `systemic_policy_collective_action.child.3f73e22d16` | climateemergency | Direct child |
| `systemic_policy_collective_action.child.12d4ae0b64` | climateaction | Direct child |
| `systemic_policy_collective_action.child.711415eb43` | sustainable | Direct child |
| `systemic_policy_collective_action.child.d32b003271` | climatestrike | Direct child |
| `systemic_policy_collective_action.child.c82d32b13d` | climatedenial | Direct child |
| `systemic_policy_collective_action.child.f300f10844` | greenhouse | Direct child |
| `systemic_policy_collective_action.child.8742935ee8` | food security | Direct child |
| `v3_3_192` | green space | Direct child |
| `v3_3_193` | tree canopy | Direct child |
| `v3_3_194` | green spaces | Direct child |
| `v3_3_195` | community garden | Direct child |
| `v3_3_196` | community gardens | Direct child |
| `v3_3_200` | community resilience | Direct child |
| `v3_3_201` | urban forest | Direct child |
| `v3_3_203` | neighbourhood centre | Direct child |
| `v3_3_204` | mutual aid | Direct child |
| `v3_3_205` | neighbourhood house | Direct child |
| `v3_4_206` | tree cover | Direct child |
| `v3_4_207` | on country | Direct child |
| `v3_4_209` | community-led | Direct child |
| `v3_4_212` | urban greening | Direct child |
| `v3_4_214` | caring for country | Direct child |
| `v3_4_216` | disaster recovery | Direct child |
| `v3_4_218` | shade trees | Direct child |
| `v3_4_220` | cultural burning | Direct child |
| `v3_5_231` | grassroots | Direct child |
| `v3_5_242` | community action | Direct child |
| `v3_5_243` | landcare | Direct child |
| `v3_5_244` | natural regeneration | Direct child |
| `systemic_policy_collective_action.child.aa7f971909` | old growth forests | Direct child |
| `systemic_policy_collective_action.child.f808060cd4` | intergenerational | Direct child |
| `systemic_policy_collective_action.child.9b93ebd2dd` | future generations | Direct child |
| `systemic_policy_collective_action.child.a4754f1384` | collective action | Direct child |
| `systemic_policy_collective_action.child.d9031c7a59` | stewardship | Direct child |
| `systemic_policy_collective_action.child.e626aaca08` | ecocide | Direct child |
| `systemic_policy_collective_action.child.decbdfce1a` | slow violence | Direct child |
| `systemic_policy_collective_action.child.ec0d85521d` | fossil capitalism | Direct child |
| `systemic_policy_collective_action.child.396e9ba2be` | regeneration | Direct child |
| `systemic_policy_collective_action.child.7d513d41f8` | climate safe future | Direct child |
| `systemic_policy_collective_action.child.1b78a1ee99` | environmental footprint | Direct child |
| `systemic_policy_collective_action.child.15f3f98bfc` | regenerative agriculture | Direct child |
| `systemic_policy_collective_action.child.continuum.f84ceb42abd0` | climate scaremongering | continuum_policy_cultural_backlash |
| `systemic_policy_collective_action.child.continuum.9e789b4fdcb5` | climate scare mongering | continuum_policy_cultural_backlash |
| `systemic_policy_collective_action.child.continuum.6ff63d71323c` | climate alarmists | continuum_policy_cultural_backlash |
| `systemic_policy_collective_action.child.continuum.3eba6b9fa6f0` | climate hysteria | continuum_policy_cultural_backlash |
| `systemic_policy_collective_action.child.continuum.1ad0218bd976` | sick of climate alarmism | continuum_policy_cultural_backlash |
| `systemic_policy_collective_action.child.continuum.72c7a2abc7f0` | climate fearmongering | continuum_policy_cultural_backlash |
| `systemic_policy_collective_action.child.continuum.4a25d9c543e2` | climate fear mongering | continuum_policy_cultural_backlash |
| `systemic_policy_collective_action.child.continuum.2f8ece24d8f5` | climate scientists are wrong | continuum_policy_cultural_backlash |
| `systemic_policy_collective_action.child.continuum.d87e5bb49fac` | fear of the carbon tax | continuum_policy_cultural_backlash |
| `systemic_policy_collective_action.child.continuum.70de5e64e249` | angry about climate policy | continuum_policy_cultural_backlash |
| `systemic_policy_collective_action.child.continuum.6bd23301a86e` | net zero madness | continuum_policy_cultural_backlash |
| `systemic_policy_collective_action.child.continuum.2aa419ba6be4` | climate propaganda | continuum_policy_cultural_backlash |

### continuum_policy_cultural_backlash

Canonical assignments: **12**. Declared discovery expressions: **12**.

`climate scaremongering`; `climate scare mongering`; `climate alarmists`; `climate hysteria`; `sick of climate alarmism`; `climate fearmongering`; `climate fear mongering`; `climate scientists are wrong`; `fear of the carbon tax`; `angry about climate policy`; `net zero madness`; `climate propaganda`.

## Weather, ecology & fire-risk context

Parent ID: `weather_uv_fire_risk_context`.

### Standalone base terms

- `UV`
- `UV index`
- `ultraviolet`
- `BOM`
- `Bureau of Meteorology`
- `fire danger`
- `total fire ban`
- `fire ban`
- `TFB`
- `TOBAN`
- `bushfire risk`
- `bushfire warning`
- `catastrophic fire`
- `feels like`
- `apparent temperature`
- `wet bulb`
- `wet-bulb`

### Canonical children

| Child ID | Expression | Sub-parent |
|---|---|---|
| `weather_uv_fire_risk_context.child.26dd54b2bf` | bushfire | Direct child |
| `weather_uv_fire_risk_context.child.15c161b33b` | bushfires | Direct child |
| `weather_uv_fire_risk_context.child.e6133749bc` | bush fire | Direct child |
| `weather_uv_fire_risk_context.child.ea96a4e510` | bush fires | Direct child |
| `weather_uv_fire_risk_context.child.c24ed396cb` | bush-fire | Direct child |
| `weather_uv_fire_risk_context.child.78c860e144` | bush-fires | Direct child |
| `weather_uv_fire_risk_context.child.fee5861463` | wildfire | Direct child |
| `weather_uv_fire_risk_context.child.aafd7f1844` | wildfires | Direct child |
| `weather_uv_fire_risk_context.child.d2977974a2` | wild fire | Direct child |
| `weather_uv_fire_risk_context.child.93a7301c1b` | wild fires | Direct child |
| `weather_uv_fire_risk_context.child.dc9f28b12d` | fire | Direct child |
| `weather_uv_fire_risk_context.child.03ce67f208` | fires | Direct child |
| `weather_uv_fire_risk_context.child.5221409b64` | burning | Direct child |
| `weather_uv_fire_risk_context.child.8bd1c5cb83` | burnt | Direct child |
| `weather_uv_fire_risk_context.child.2f79ea62c0` | burned | Direct child |
| `weather_uv_fire_risk_context.child.04d588cb41` | smoke | Direct child |
| `weather_uv_fire_risk_context.child.079f66fe29` | smoky | Direct child |
| `weather_uv_fire_risk_context.child.d443268885` | smokey | Direct child |
| `weather_uv_fire_risk_context.child.840ee9db4c` | haze | Direct child |
| `weather_uv_fire_risk_context.child.d6bbbd5701` | air quality | Direct child |
| `weather_uv_fire_risk_context.child.79686ca3c3` | air pollution | Direct child |
| `weather_uv_fire_risk_context.child.41afa10d45` | hazardous air | Direct child |
| `weather_uv_fire_risk_context.child.4c41634056` | dust storm | Direct child |
| `weather_uv_fire_risk_context.child.caaed8c4eb` | drought | Direct child |
| `weather_uv_fire_risk_context.child.8a43043943` | dry spell | Direct child |
| `weather_uv_fire_risk_context.child.7711bbc014` | dry weather | Direct child |
| `weather_uv_fire_risk_context.child.d3841d8dba` | megafire | Direct child |
| `weather_uv_fire_risk_context.child.690d257bf5` | melbournesmoke | Direct child |
| `weather_uv_fire_risk_context.child.7333615738` | nswfires | Direct child |
| `weather_uv_fire_risk_context.child.af1577b581` | vicfires | Direct child |
| `weather_uv_fire_risk_context.child.7663dd4cd3` | nswbushfires | Direct child |
| `weather_uv_fire_risk_context.child.83c43621da` | black summer | Direct child |
| `weather_uv_fire_risk_context.child.79667d66ac` | airpollution | Direct child |
| `v3_4_211` | floodwaters | Direct child |
| `v3_4_221` | flood waters | Direct child |
| `v3_4_225` | monsoon | Direct child |
| `v3_4_227` | storm surge | Direct child |
| `v3_4_230` | tropical cyclone | Direct child |
| `v3_5_234` | flood recovery | Direct child |
| `v3_5_241` | flood-prone | Direct child |
| `v3_5_251` | fire-prone | Direct child |
| `weather_uv_fire_risk_context.child.91bcb5a9bb` | rainfall | Direct child |
| `weather_uv_fire_risk_context.child.67df277e25` | south-westerly | Direct child |
| `weather_uv_fire_risk_context.child.3d67e12373` | salinity | Direct child |
| `weather_uv_fire_risk_context.child.733a3ccb44` | bushfire smoke | Direct child |
| `weather_uv_fire_risk_context.child.a2e743cfc7` | bushfire season | Direct child |
| `weather_uv_fire_risk_context.child.4eeca7d540` | cool change | Direct child |
| `weather_uv_fire_risk_context.child.e000854a88` | dried out | Direct child |
| `weather_uv_fire_risk_context.child.9e38ddd653` | drying out | Direct child |
| `weather_uv_fire_risk_context.child.d4f0d8e319` | overcast | Direct child |
| `weather_uv_fire_risk_context.child.424f22be65` | drizzle | Direct child |
| `weather_uv_fire_risk_context.child.8744bbc753` | thermometer | Direct child |
| `weather_uv_fire_risk_context.child.6f5e90519c` | firestorm | Direct child |
| `weather_uv_fire_risk_context.child.3adf0cc810` | easterly | Direct child |
| `weather_uv_fire_risk_context.child.921a95e8b6` | sunlight | Direct child |
| `weather_uv_fire_risk_context.child.8038ffc6ee` | droughts | Direct child |
| `weather_uv_fire_risk_context.child.d7bf0c9ea6` | frost | Direct child |
| `weather_uv_fire_risk_context.child.01dd2f7dcb` | hazy | Direct child |
| `weather_uv_fire_risk_context.child.c551e04110` | downpour | Direct child |
| `weather_uv_fire_risk_context.child.e8a1710cbc` | aridity | Direct child |
| `weather_uv_fire_risk_context.child.8f634dd5f5` | coastal erosion | Direct child |
| `weather_uv_fire_risk_context.child.4c706a66ce` | drought-stricken | Direct child |
| `weather_uv_fire_risk_context.child.76c74433fc` | land clearing | Direct child |
| `weather_uv_fire_risk_context.child.d0a206ab81` | biodiversity loss | Direct child |
| `weather_uv_fire_risk_context.child.3ef2e0de26` | resource depletion | Direct child |
| `weather_uv_fire_risk_context.child.2220493ab6` | environmental degradation | Direct child |
| `weather_uv_fire_risk_context.child.80ba35b21a` | weathering | Direct child |
| `weather_uv_fire_risk_context.child.ed8aed8f06` | evacuation centre | Direct child |

Cultural learning declares 12 discovery expressions but assigns eight canonical new children; four were already present elsewhere. Do not double-count declared expressions as new children.
