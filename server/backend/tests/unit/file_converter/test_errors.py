"""Unit tests for user-notification error descriptions."""

from mascope_backend.file_converter.errors import describe_exception


class TestDescribeException:
    def test_bare_keyerror_gets_class_name(self):
        # str(KeyError('Configuration File')) is just "'Configuration File'" -
        # meaningless in a toast without the class name.
        try:
            raise KeyError("Configuration File")
        except KeyError as e:
            assert describe_exception(e) == "KeyError: 'Configuration File'"

    def test_empty_message_falls_back_to_class_name(self):
        assert describe_exception(ValueError()) == "ValueError"

    def test_sentence_message_stays_unprefixed(self):
        e = RuntimeError("File converter service is not available")
        assert describe_exception(e) == "File converter service is not available"

    def test_single_token_message_gets_class_name(self):
        assert describe_exception(ValueError("m/z")) == "ValueError: m/z"
