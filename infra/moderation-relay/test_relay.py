import tempfile,unittest
from pathlib import Path
from relay import Journal,category,activity,legendary
import json
class RelayTest(unittest.TestCase):
 def test_occurrences_survive_restart_and_deduplicate(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'state.sqlite';j=Journal(path)
   e=dict(id='mc:1',platform='Minecraft',target='p1',name='Player',actor='Staff',reason='FLOOD',action='MUTE',date='2026-10-22T12:00:00',end=None,punitive=True)
   j.add(e);j.add(e);self.assertEqual(len(j.pending()),1)
   j.add(dict(e,id='mc:2',reason='Flood no chat',date='2026-10-22T13:00:00'))
   j.add(dict(e,id='mc-revoke:1',punitive=False,date='2026-10-22T14:00:00'))
   j.db.close();j=Journal(path)
   self.assertEqual(j.occurrence(dict(e,id='mc:2',date='2026-10-22T13:00:00')),2)
   self.assertEqual(j.occurrence(dict(e,platform='Discord')),0)
 def test_activity_offset_and_partial_records(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);j=Journal(root/'state.sqlite')
   e=dict(id='event-1',uuid='player',actor='Player',kind='CHAT',channel='global',text='Olá',date='2026-10-22T12:00:00Z')
   log=root/'2026-10-22.jsonl';log.write_text(json.dumps(e)+'\n'+json.dumps(dict(e,id='event-2')))
   activity(j,root);self.assertEqual(len(j.pending()),1)
   activity(j,root);self.assertEqual(len(j.pending()),1)
   with log.open('a') as f:f.write('\n')
   activity(j,root);self.assertEqual(len(j.pending()),2)
 def test_legendary_payload_is_durable_and_not_a_moderation_occurrence(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);j=Journal(root/'state.sqlite')
   payload={'embeds':[{'title':'Aparição lendária'}],'allowed_mentions':{'parse':[]}}
   e=dict(id='legend-1',kind='SPAWN',date='2026-10-22T12:00:00Z',payload=payload)
   (root/'2026-10-22.jsonl').write_text(json.dumps(e)+'\n')
   legendary(j,root);legendary(j,root)
   self.assertEqual(len(j.pending()),1)
   row=json.loads(j.pending()[0][1]);self.assertEqual(row['webhook'],payload)
   self.assertFalse(row['punitive'])
 def test_classification(self):
  self.assertEqual(category('Assédio'),'Assédio')
  self.assertEqual(category('spam no chat'),'Flood/spam')
if __name__=='__main__':unittest.main()
