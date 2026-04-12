from mista_wispa.cleanup import rule_based_cleanup


def test_removes_filler_words():
    assert rule_based_cleanup("I um think this is uh good") == "I think this is good"


def test_removes_filler_phrases():
    assert rule_based_cleanup("You know I mean it was basically fine") == "It was fine"


def test_normalizes_whitespace():
    assert rule_based_cleanup("hello   world") == "Hello world"


def test_fixes_double_punctuation():
    assert rule_based_cleanup("hello..  world") == "Hello. World"


def test_capitalizes_after_sentence_end():
    assert rule_based_cleanup("first sentence. second sentence") == "First sentence. Second sentence"


def test_capitalizes_first_word():
    assert rule_based_cleanup("hello world") == "Hello world"


def test_empty_input():
    assert rule_based_cleanup("") == ""


def test_only_fillers():
    assert rule_based_cleanup("um uh like") == ""


def test_preserves_meaning():
    assert rule_based_cleanup("The meeting is at 3 PM.") == "The meeting is at 3 PM."


def test_filler_at_start():
    assert rule_based_cleanup("So basically the plan is good") == "The plan is good"


def test_question_mark_capitalization():
    assert rule_based_cleanup("is it done? yes it is") == "Is it done? Yes it is"


def test_exclamation_capitalization():
    assert rule_based_cleanup("wow! that is great") == "Wow! That is great"
