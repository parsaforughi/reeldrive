import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from bot.services.hikerapi import extract_story_items
from bot.services.instagram import InstagramDownloader, _story_id_matches
from bot.utils import (
    is_story_media_url,
    parse_command,
    parse_media_url,
    parse_story_ref,
)


class StoryUrlParsingTests(unittest.TestCase):
    def test_story_link_with_id_is_a_media_url(self) -> None:
        url = (
            "https://www.instagram.com/stories/cristiano/"
            "1234567890123456789/?utm_source=ig_story_item_share"
        )
        parsed = parse_command(url)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.kind, "media_url")
        self.assertEqual(
            parsed.url,
            "https://www.instagram.com/stories/cristiano/1234567890123456789/",
        )
        ref = parse_story_ref(url)
        self.assertIsNotNone(ref)
        assert ref is not None
        self.assertEqual(ref.kind, "story")
        self.assertEqual(ref.username, "cristiano")
        self.assertEqual(ref.media_id, "1234567890123456789")

    def test_story_link_without_id_uses_username(self) -> None:
        parsed = parse_command("instagram.com/stories/nasa")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.kind, "media_url")
        self.assertTrue(is_story_media_url(parsed.url or ""))
        ref = parse_story_ref(parsed.url or "")
        self.assertIsNotNone(ref)
        assert ref is not None
        self.assertEqual(ref.username, "nasa")
        self.assertIsNone(ref.media_id)

    def test_highlight_and_share_links(self) -> None:
        highlight = parse_story_ref(
            "https://www.instagram.com/stories/highlights/17901234567890123/"
        )
        self.assertIsNotNone(highlight)
        assert highlight is not None
        self.assertEqual(highlight.kind, "highlight")
        self.assertEqual(highlight.media_id, "17901234567890123")

        share = parse_media_url(
            "https://www.instagram.com/s/aGlnaGxpZ2h0OjE4MTQ2MjE2Njk4MDIyMTc0"
        )
        self.assertEqual(
            share,
            "https://www.instagram.com/s/aGlnaGxpZ2h0OjE4MTQ2MjE2Njk4MDIyMTc0/",
        )
        self.assertTrue(is_story_media_url(share or ""))

    def test_redirect_and_reel_links_still_work(self) -> None:
        wrapped = (
            "https://l.instagram.com/?u="
            "https%3A%2F%2Fwww.instagram.com%2Fstories%2Fnasa%2F99%2F"
        )
        self.assertEqual(
            parse_media_url(wrapped),
            "https://www.instagram.com/stories/nasa/99/",
        )
        self.assertEqual(
            parse_media_url("https://www.instagram.com/reel/AbC123xyz/"),
            "https://www.instagram.com/reel/AbC123xyz/",
        )
        self.assertFalse(is_story_media_url("https://www.instagram.com/reel/AbC123xyz/"))

    def test_stories_command_still_works(self) -> None:
        parsed = parse_command("استوری nasa")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.kind, "stories")
        self.assertEqual(parsed.username, "nasa")


class StoryPayloadTests(unittest.TestCase):
    def test_extract_story_items_unwraps_reel(self) -> None:
        items = extract_story_items(
            {
                "reel": {
                    "items": [
                        {"pk": "1", "media_type": 1, "thumbnail_url": "https://x/a.jpg"}
                    ]
                },
                "status": "ok",
            }
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["pk"], "1")

    def test_story_id_matches_pk_and_compound_id(self) -> None:
        self.assertTrue(_story_id_matches({"pk": 99, "id": "99_1"}, "99"))
        self.assertFalse(_story_id_matches({"pk": 11}, "99"))


class StoryDownloadRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_story_link_uses_story_endpoint_not_media(self) -> None:
        downloader = InstagramDownloader()
        story = {
            "pk": "1234567890123456789",
            "media_type": 1,
            "thumbnail_url": "https://cdn.example/story.jpg",
            "taken_at": "2026-09-05T10:00:00Z",
        }
        fake_path = Path("/tmp/reeldrive/story.jpg")
        with (
            patch(
                "bot.services.instagram.hiker_client.fetch_story_by_url",
                new=AsyncMock(return_value=[story]),
            ) as story_fetch,
            patch(
                "bot.services.instagram.hiker_client.fetch_media_by_url",
                new=AsyncMock(),
            ) as media_fetch,
            patch.object(
                downloader,
                "_download_story_items",
                new=AsyncMock(
                    return_value=[
                        type(
                            "Item",
                            (),
                            {
                                "path": fake_path,
                                "is_video": False,
                                "taken_at": "2026-09-05 10:00",
                                "direct_url": "https://cdn.example/story.jpg",
                            },
                        )()
                    ]
                ),
            ),
        ):
            result = await downloader.download_media_url(
                "https://www.instagram.com/stories/nasa/1234567890123456789/"
            )

        story_fetch.assert_awaited_once()
        media_fetch.assert_not_awaited()
        self.assertEqual(result.media_type, "photo")
        self.assertEqual(result.paths, [fake_path])

    async def test_expired_story_link_raises_story_not_found(self) -> None:
        downloader = InstagramDownloader()
        from bot.services.hikerapi import HikerNotFoundError

        with (
            patch(
                "bot.services.instagram.hiker_client.fetch_story_by_url",
                new=AsyncMock(side_effect=HikerNotFoundError("gone")),
            ),
            patch(
                "bot.services.instagram.hiker_client.fetch_story_by_id",
                new=AsyncMock(side_effect=HikerNotFoundError("gone")),
            ),
            patch.object(
                downloader,
                "_fetch_story_dicts",
                new=AsyncMock(return_value=[]),
            ),
        ):
            with self.assertRaises(ValueError) as ctx:
                await downloader.download_media_url(
                    "https://www.instagram.com/stories/nasa/123/"
                )
        self.assertEqual(str(ctx.exception), "story_not_found")


if __name__ == "__main__":
    unittest.main()
