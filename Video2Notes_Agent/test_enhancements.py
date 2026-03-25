import unittest
import sys
import types

sys.modules.setdefault("litellm", types.SimpleNamespace())

from analyzer import AnalyzedChunk
from config import Config
from hybrid_search import HybridSearchRanker
from note_structuring import structure_analyzed_chunks
from source_utils import canonicalize_url, extract_google_drive_file_id
from synthesizer import NotesSynthesizer
from transcriber import TranscriptChunk, TranscriptSegment
from export_service import build_export_markdown


def make_chunk(title: str, key_points: list[str], concepts: list[str], actions: list[str], start: float):
    chunk = TranscriptChunk(
        index=int(start),
        segments=[
            TranscriptSegment(text="Example text", start=start, end=start + 30),
        ],
    )
    return AnalyzedChunk(
        chunk=chunk,
        classification="CORE",
        importance_score=8,
        key_points=key_points,
        concepts=concepts,
        action_items=actions,
        section_title=title,
    )


class SourceUtilityTests(unittest.TestCase):
    def test_google_drive_file_id_extraction(self):
        url = "https://drive.google.com/file/d/abc123XYZ/view?usp=sharing"
        self.assertEqual(extract_google_drive_file_id(url), "abc123XYZ")

    def test_playlist_detection(self):
        details = canonicalize_url("https://www.youtube.com/watch?v=abc12345678&list=PL123")
        self.assertTrue(details.is_playlist)
        self.assertEqual(details.source_type, "youtube_playlist")

    def test_google_drive_folder_rejected(self):
        with self.assertRaises(ValueError):
            canonicalize_url("https://drive.google.com/drive/folders/abc123")


class StructuringTests(unittest.TestCase):
    def test_duplicate_sections_are_merged(self):
        sections = structure_analyzed_chunks(
            [
                make_chunk("Intro to Caching", ["Reuse transcripts"], ["Cache"], ["Enable reuse"], 0),
                make_chunk("Intro to caching", ["Reuse transcripts"], ["Cache"], ["Enable reuse"], 40),
            ]
        )
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0].key_points, ["Reuse transcripts"])


class ExportTests(unittest.TestCase):
    def test_obsidian_export_includes_frontmatter(self):
        payload = build_export_markdown(
            "Test Notes",
            "Desc",
            "# Body",
            {},
            "default",
            "markdown_obsidian",
            True,
            True,
            False,
        )
        self.assertTrue(payload.startswith("---"))
        self.assertIn('title: "Test Notes"', payload)


class SynthesizerTests(unittest.TestCase):
    def test_non_executive_styles_request_overview_section(self):
        config = Config(note_style="study_notes")
        synthesizer = NotesSynthesizer(config)
        prompt = synthesizer.build_markdown_prompt([], "Demo", 120)
        self.assertIn("Overview section", prompt)
        self.assertNotIn("Executive Summary section", prompt)


class HybridSearchTests(unittest.TestCase):
    def test_hybrid_search_prefers_keyword_relevant_result(self):
        results = HybridSearchRanker.rank(
            "cache transcripts",
            [
                {"title": "Cooking tips", "body": "Fresh herbs and sauces"},
                {"title": "Transcript cache", "body": "Reuse transcripts across note styles"},
            ],
            lambda item: f"{item['title']} {item['body']}",
        )
        self.assertEqual(results[0]["title"], "Transcript cache")


if __name__ == "__main__":
    unittest.main()
