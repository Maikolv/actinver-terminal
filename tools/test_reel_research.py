import unittest
import pandas as pd
from reel_research import features, validate


class OfflineResearchTests(unittest.TestCase):
    def fixture(self):
        rows=[]
        for i in range(90):
            price=100+i*.2+(i%7)*.1
            rows.append(dict(timestamp=pd.Timestamp('2026-01-01',tz='UTC')+pd.Timedelta(minutes=i),open=price,high=price+1,low=price-.5,close=price+.7,volume=100+i))
        return pd.DataFrame(rows)

    def test_prefix_does_not_change(self):
        source=self.fixture()
        full=features(source)
        for n in [35,48,67]:
            pd.testing.assert_frame_equal(full.iloc[:n].reset_index(drop=True),features(source.iloc[:n]))

    def test_known_gap_requires_third_bar(self):
        source=self.fixture()
        source.loc[40,['open','high','low','close']]=[110,112,109,111]
        source.loc[41,['open','high','low','close']]=[113,115,112.5,114]
        source.loc[42,['open','high','low','close']]=[116,118,115.5,117]
        out=features(source)
        self.assertEqual(out.loc[42,'fvg_confirmed'],1)
        self.assertEqual(out.loc[42,'fvg_top'],115.5)
        self.assertEqual(out.loc[42,'fvg_bottom'],112)
        self.assertNotIn('MitigatedIndex',out)

    def test_invalid_data_rejected(self):
        for col,value in [('close',float('nan')),('volume',-1),('high',1)]:
            data=self.fixture();data.loc[20,col]=value
            with self.assertRaises(ValueError):validate(data)
        data=self.fixture();data.loc[20,'timestamp']=data.loc[19,'timestamp']
        with self.assertRaises(ValueError):validate(data)

    def test_warmup_is_missing(self):
        out=features(self.fixture())
        self.assertTrue(out.sma20.iloc[:19].isna().all())
        self.assertTrue(out.atr14.iloc[:13].isna().all())

    def test_missing_bar_does_not_create_gap(self):
        source=self.fixture()
        source.loc[40,['open','high','low','close']]=[110,112,109,111]
        source.loc[41,['open','high','low','close']]=[113,115,112.5,114]
        source.loc[42,['open','high','low','close']]=[116,118,115.5,117]
        source.loc[42:,'timestamp'] += pd.Timedelta(minutes=10)
        self.assertTrue(pd.isna(features(source).loc[42,'fvg_confirmed']))


if __name__=='__main__':unittest.main()
