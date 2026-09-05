import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from bot.services.hikerapi import extract_highlight_tray, extract_story_items
from bot.services.instagram import InstagramDownloader, _story_id_matches
from bot.utils import (
    decode_instagram_share_code,
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
        share_ref = parse_story_ref(share or "")
        self.assertIsNotNone(share_ref)
        assert share_ref is not None
        self.assertEqual(share_ref.kind, "highlight")
        self.assertEqual(
            decode_instagram_share_code("aGlnaGxpZ2h0OjE4MTQ2MjE2Njk4MDIyMTc0"),
            ("highlight", share_ref.media_id),
        )
        self.assertTrue((share_ref.media_id or "").isdigit())

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

    def test_extract_highlight_tray_unwraps_response(self) -> None:
        tray = extract_highlight_tray(
            {
                "response": {
                    "tray": [{"pk": "1790", "title": "Travel", "items": []}],
                    "status": "ok",
                }
            }
        )
        self.assertEqual(len(tray), 1)
        self.assertEqual(tray[0]["title"], "Travel")

    def test_extract_story_items_unwraps_nested_media(self) -> None:
        items = extract_story_items(
            [{"media": {"pk": "8", "media_type": 1, "thumbnail_url": "https://x/b.jpg"}}]
        )
        self.assertEqual(items[0]["pk"], "8")


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

    async def test_highlight_link_uses_highlight_endpoint(self) -> None:
        downloader = InstagramDownloader()
        item = {
            "pk": "88",
            "media_type": 1,
            "thumbnail_url": "https://cdn.example/hl.jpg",
        }
        fake_path = Path("/tmp/reeldrive/hl.jpg")
        with (
            patch(
                "bot.services.instagram.hiker_client.fetch_highlight_by_id",
                new=AsyncMock(return_value=[item]),
            ) as highlight_fetch,
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
                                "taken_at": "",
                                "direct_url": "https://cdn.example/hl.jpg",
                            },
                        )()
                    ]
                ),
            ),
        ):
            result = await downloader.download_media_url(
                "https://www.instagram.com/stories/highlights/17901234567890123/"
            )

        highlight_fetch.assert_awaited_once_with("17901234567890123")
        media_fetch.assert_not_awaited()
        self.assertEqual(result.media_type, "photo")

    async def test_highlight_index_fetches_items_by_id_when_tray_empty(self) -> None:
        downloader = InstagramDownloader()
        media = {
            "pk": "9",
            "media_type": 1,
            "thumbnail_url": "https://cdn.example/c.jpg",
        }
        with (
            patch(
                "bot.services.instagram.hiker_client.fetch_user_highlights",
                new=AsyncMock(return_value=[{"pk": "1790", "title": "X", "items": []}]),
            ),
            patch(
                "bot.services.instagram.hiker_client.fetch_highlight_by_id",
                new=AsyncMock(return_value=[media]),
            ) as by_id,
            patch.object(
                downloader,
                "_download_story_items",
                new=AsyncMock(return_value=["downloaded"]),
            ),
        ):
            result = await downloader.download_highlight_by_index("nasa", 1)

        by_id.assert_awaited_once_with("1790")
        self.assertEqual(result, ["downloaded"])


if __name__ == "__main__":
    unittest.main()
