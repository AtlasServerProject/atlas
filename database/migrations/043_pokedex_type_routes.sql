ALTER TABLE pokedex_rewards ADD COLUMN IF NOT EXISTS route TEXT NOT NULL DEFAULT 'main';
ALTER TABLE pokedex_rewards DROP CONSTRAINT IF EXISTS pokedex_rewards_uuid_milestone_part_key;
ALTER TABLE pokedex_rewards DROP CONSTRAINT IF EXISTS pokedex_rewards_milestone_check;
ALTER TABLE pokedex_rewards ADD CONSTRAINT pokedex_rewards_route_milestone_check CHECK((route='main' AND milestone BETWEEN 10 AND 100 AND milestone%10=0) OR (route IN ('normal','fire','water','electric','grass','ice','fighting','poison','ground','flying','psychic','bug','rock','ghost','dragon','dark','steel','fairy') AND milestone IN (10,25,50,75,100)));
ALTER TABLE pokedex_rewards ADD CONSTRAINT pokedex_rewards_route_part_key UNIQUE(uuid,route,milestone,part);
CREATE TABLE pokedex_type_progress (
 uuid UUID NOT NULL,type TEXT NOT NULL CHECK(type IN ('normal','fire','water','electric','grass','ice','fighting','poison','ground','flying','psychic','bug','rock','ghost','dragon','dark','steel','fairy')),
 milestone INTEGER NOT NULL CHECK(milestone IN (0,10,25,50,75,100)),caught INTEGER NOT NULL CHECK(caught>=0),total INTEGER NOT NULL CHECK(total>0),completed_at TIMESTAMPTZ,selected BOOLEAN NOT NULL DEFAULT FALSE,PRIMARY KEY(uuid,type)
);
CREATE UNIQUE INDEX pokedex_one_type_title ON pokedex_type_progress(uuid) WHERE selected;
