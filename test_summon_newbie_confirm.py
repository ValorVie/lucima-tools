"""Offline regression checks for newbie summon confirmation."""

import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend import appcore


class FakeClient:
    def __init__(self, buy_count):
        self.buy_count = buy_count
        self.confirm_numbers = []
        self.account_state = {
            "StoreRecordContainer": {
                "Records": [{"Store": "Summon", "StaticID": "SummonNewbie", "BuyCount": 2}]
            }
        }

    def _auth_data(self, data):
        return data

    def call(self, route, data):
        if route == "StoreHandler.BuyCommodity":
            commodity = {} if self.buy_count is None else {"BuyCount": self.buy_count}
            return {
                "CommodityRecord": commodity,
                "SelectiveSummonRecord": {
                    "RecordNumber": 0,
                    "Rewarded": False,
                    "NowDropResult": {"Items": [
                        {"RoleData": {"StaticID": "H014", "Star": 5}},
                        {"RoleData": {"StaticID": "H029", "Star": 4}},
                    ]},
                },
            }
        if route == "SelectiveSummonRecordHandler.DropSummonRecord":
            self.confirm_numbers.append(data["RecordNumber"])
            if data["RecordNumber"] != self.buy_count:
                raise RuntimeError("RecordNumber Not Same")
            return {"SelectiveSummonRecord": {"Rewarded": True}}
        raise AssertionError(route)


class NewbieConfirmTests(unittest.TestCase):
    def reroll(self, buy_count):
        client = FakeClient(buy_count)
        account = SimpleNamespace(client=client, lock=threading.Lock())
        with patch.object(appcore.config, "check_dev_pass", return_value=True), \
             patch.object(appcore, "_require", return_value=account), \
             patch.object(appcore, "item_name", side_effect=lambda sid: sid):
            result = appcore.dev_summon_newbie_reroll(
                "test", ["H014", "H029"], max_rolls=1, confirm_on_match=True,
            )
        return result, client

    def test_confirm_uses_updated_buy_count(self):
        result, client = self.reroll(3)
        self.assertTrue(result["ok"])
        self.assertTrue(result["confirmed"])
        self.assertEqual(result["result"]["recordNumber"], 0)
        self.assertEqual(result["result"]["buyCount"], 3)
        self.assertEqual(client.confirm_numbers, [3])

    def test_missing_buy_count_stops_before_confirm(self):
        result, client = self.reroll(None)
        self.assertFalse(result["ok"])
        self.assertTrue(result["matched"])
        self.assertFalse(result["confirmed"])
        self.assertIn("CommodityRecord.BuyCount", result["error"])
        self.assertEqual(client.confirm_numbers, [])


if __name__ == "__main__":
    unittest.main()
