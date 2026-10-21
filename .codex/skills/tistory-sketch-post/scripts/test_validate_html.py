"""Offline regression tests; no browser, network, credentials, or uploader."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from validate_html import validate_html


SCRIPT = Path(__file__).with_name("validate_html.py")


class ValidateHtmlTests(unittest.TestCase):
    def test_void_tags_and_comments_do_not_need_closing_tags(self):
        self.assertEqual([], validate_html(
            '<meta charset="utf-8"><div><!-- <div><svg><path> -->'
            '<p>text<br><img src="image.png"><hr/><input disabled></p></div>'
        ))

    def test_mixed_self_closing_svg_elements(self):
        self.assertEqual([], validate_html(
            '<div><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<defs><marker id="arrow"/><linearGradient id="shade">'
            '<stop offset="0"/></linearGradient></defs>'
            '<path d="M0 0L10 10"/><circle cx="10" cy="10" r="2"/>'
            '<text>one &amp; two &#160; three</text></svg><br/></div><svg/>'
        ))

    def test_html_tag_names_are_case_insensitive(self):
        self.assertEqual([], validate_html('<DIV><P>text<BR></p></div>'))

    def test_broken_explicit_nesting(self):
        self.assertTrue(validate_html('<div><p>text</div></p>'))

    def test_unclosed_tags(self):
        self.assertTrue(validate_html('<div><p>text</p>'))
        self.assertTrue(validate_html('<div><svg><path/></svg>'))

    def test_incomplete_tag(self):
        self.assertTrue(validate_html('<div'))
        self.assertTrue(validate_html('<!-- incomplete comment'))

    def test_non_void_html_self_closing_tag_is_rejected(self):
        self.assertTrue(validate_html('<div/>'))

    def test_invalid_svg_xml_and_entities(self):
        for source in (
            '<svg><path></svg>',
            '<svg><text>&unknown;</text></svg>',
            '<svg><text>one & two</text></svg>',
            '<svg><text>&#0;</text></svg>',
            '<svg><path d="one" d="two"/></svg>',
        ):
            with self.subTest(source=source):
                self.assertTrue(validate_html(source))

    def test_svg_tag_names_remain_case_sensitive(self):
        errors = validate_html('<svg><linearGradient></lineargradient></svg>')
        self.assertTrue(any('invalid SVG XML' in error for error in errors))

    def test_duplicate_ids_across_svgs(self):
        errors = validate_html('<svg><marker id="arrow"/></svg><svg><path id="arrow"/></svg>')
        self.assertTrue(any('duplicate SVG id' in error for error in errors))
        self.assertEqual([], validate_html('<svg><marker id="arrow-1"/></svg><svg><path id="arrow-2"/></svg>'))
        self.assertTrue(validate_html('<svg><marker id="same"/><path id="same"/></svg>'))

    def test_svg_text_in_comments_is_ignored(self):
        self.assertEqual([], validate_html('<!-- <svg><path id="same"/></svg> -->'
                                          '<svg><!-- <path id="same"/> --><path id="same"/></svg>'))

    def test_tag_like_text_in_raw_style_and_script_is_ignored(self):
        self.assertEqual([], validate_html('<style>.a::before { content: "<div>"; }</style>'
                                          '<script>const example = "<svg><path>";</script>'))

    def test_cli_accepts_multiple_valid_paths_and_is_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ('first.html', 'second.html')]
            contents = ['<div>one<br></div>', '<svg><path/></svg>']
            for path, content in zip(paths, contents):
                path.write_text(content, encoding='utf-8')
            result = subprocess.run([sys.executable, '-B', str(SCRIPT), *map(str, paths)],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual('', result.stderr)
            self.assertEqual(contents, [path.read_text(encoding='utf-8') for path in paths])

    def test_cli_returns_nonzero_for_invalid_and_missing_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / 'invalid.html'
            invalid.write_text('<div><p></div>', encoding='utf-8')
            result = subprocess.run([sys.executable, '-B', str(SCRIPT), str(invalid), str(invalid) + '.missing'],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(1, result.returncode)
            self.assertIn('does not match', result.stderr)
            self.assertIn('.missing', result.stderr)


if __name__ == '__main__':
    unittest.main()
