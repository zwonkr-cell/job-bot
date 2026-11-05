# -*- coding: utf-8 -*-
"""
잡코리아 파서 회귀 테스트 — tests/fixtures 의 실제 페이지(2026-11-05 저장)로 검증합니다.
사이트가 개편되면: 새 페이지를 fixtures 에 저장하고 parse_jobs 를 고친 뒤 이 테스트로 확인하세요.
실행: python -m unittest discover -s tests -v   (리포 루트에서)
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["DRY_RUN"] = "1"

import job_bot  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures")


def fixture(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()


class ParserTest(unittest.TestCase):
    def test_list_page(self):
        jobs, rows, bad = job_bot.parse_jobs(fixture("jobkorea_list.html"))
        self.assertEqual((len(jobs), rows, bad), (40, 40, 0))
        for j in jobs:
            self.assertRegex(j["id"], r"^\d{6,}$")
            self.assertTrue(j["title"] and j["company"])
            self.assertTrue(j["link"].startswith("https://www.jobkorea.co.kr/Recruit/GI_Read/" + j["id"]))
        first = jobs[0]
        self.assertEqual(first["id"], "50310602")
        self.assertEqual(first["company"], "씨네21㈜")
        self.assertEqual(first["location"], "서울 영등포구")
        self.assertEqual(first["deadline"], "~11/20(금)")
        self.assertEqual(first["reg_time"], "1시간 전 등록")

    def test_validate(self):
        kind, (jobs, _, _) = job_bot.validate_page(200, fixture("jobkorea_list.html"))
        self.assertEqual((kind, len(jobs)), ("ok", 40))
        self.assertEqual(job_bot.validate_page(200, fixture("jobkorea_empty.html"))[0], "ok")   # 진짜 0건
        self.assertEqual(job_bot.validate_page(403, "x")[0], "blocked")
        self.assertEqual(job_bot.validate_page(200, "<html>wifi login</html>")[0], "bad")
        # 목록 마크업이 바뀌면(행 클래스 변경) '구조 변경 의심'
        changed = fixture("jobkorea_list.html").replace("devloopArea", "rowItem")
        self.assertEqual(job_bot.validate_page(200, changed)[0], "empty")

    def test_fallback_selectors(self):
        base, _, _ = job_bot.parse_jobs(fixture("jobkorea_list.html"))
        # 스크랩 버튼(data-gno)이 사라져도 상세 링크에서 공고번호를 읽음
        jobs, _, bad = job_bot.parse_jobs(fixture("jobkorea_list.html").replace("devAddScrap", "x-scrap"))
        self.assertEqual(bad, 0)
        self.assertEqual([j["id"] for j in jobs], [j["id"] for j in base])

    def test_page_url(self):
        u2 = job_bot.page_url(2)
        self.assertIn("FreePageNo=2", u2)
        self.assertIn("psTab=40", u2)
        self.assertNotIn("psTab=20", u2)
        self.assertEqual(u2.count("FreePageNo="), 1)
        self.assertIn("rOrderTab=2", u2)            # 최근 등록순 유지

    def test_collect_stops_at_known(self):
        page1 = fixture("jobkorea_list.html")

        class FakeNet(object):
            label = "direct"

            def __init__(self):
                self.calls = []

            def get(self, url, validate, budget=90):
                self.calls.append(url)
                return validate(200, page1)[1], "direct"

        jobs, _, _ = job_bot.parse_jobs(page1)
        known = {jobs[5]["id"]}
        n = FakeNet()
        state = {}
        out, rows, bad = job_bot.collect_jobs(n, state, known)
        self.assertEqual(len(n.calls), 1)          # 이미 본 공고가 있으니 1페이지에서 멈춤
        self.assertEqual(len(out), 40)
        n2 = FakeNet()
        out2, _, _ = job_bot.collect_jobs(n2, {}, {"없는-id"})
        self.assertEqual(len(n2.calls), job_bot.MAX_PAGES)   # 전부 신규면 다음 페이지까지
        self.assertEqual(len(out2), 40)            # 같은 공고는 중복 제거

    def test_message_format_unchanged(self):
        job = {"id": "1", "company": "A&B", "location": "서울", "title": "<신입>", "link": "https://x/?a=1&b=2",
               "deadline": "~11/20(금)", "reg_time": "1시간 전 등록"}
        self.assertEqual(job_bot.build_message(job),
                         "<b>A&amp;B</b> - <b>&lt;신입&gt;</b>\n\n• A&amp;B(서울)\n"
                         "• <a href='https://x/?a=1&amp;b=2'><b>&lt;신입&gt;</b></a>\n\n"
                         "⏳ ~11/20(금)\n본 공고는 1시간 전 등록됐어요")


if __name__ == "__main__":
    unittest.main(verbosity=2)
