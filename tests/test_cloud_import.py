import unittest
from cloud.import_nationwide import parse_row,STATES
class CloudImportTests(unittest.TestCase):
 def test_states(self):
  self.assertEqual(len(STATES),50)
  self.assertEqual(STATES["Minnesota"],"MN")
  self.assertEqual(STATES["New Hampshire"],"NH")
 def test_import_never_confirms(self):
  row=parse_row({"title":"Fiber crews needed","state":"Florida",
                 "source_url":"https://example.com/a","stage":"mobilizing",
                 "crew_demand_confirmed":True})
  self.assertNotIn("crew_demand_confirmed",row)
  self.assertEqual(row["state_code"],"FL")
 def test_bad_stage(self):
  with self.assertRaises(ValueError):
   parse_row({"title":"Work","source_url":"https://example.com","stage":"paid"})
if __name__=="__main__":unittest.main()
