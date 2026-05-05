import unittest

from backend.services.query_rewriter import rewrite_query


class QueryRewriterTests(unittest.TestCase):
    def test_appends_new_filter_to_previous_metric_and_time(self):
        context = {
            "previous_context": [
                {
                    "query": "Total revenue in Q1 2026",
                    "refined_query": "Total revenue in Q1 2026",
                    "response": "$2.3M",
                }
            ],
            "current_query": "What about Dearborn?",
        }

        result = rewrite_query("What about Dearborn?", context)

        self.assertTrue(result.was_rewritten)
        self.assertEqual(result.refined_query, "Total revenue in Q1 2026 for Dearborn")

    def test_replaces_existing_entity_filter(self):
        context = {
            "previous_context": [
                {
                    "query": "Total revenue in Q1 2026 for Dearborn",
                    "refined_query": "Total revenue in Q1 2026 for Dearborn",
                    "response": "$2.3M",
                }
            ],
            "current_query": "How about Claycomo?",
        }

        result = rewrite_query("How about Claycomo?", context)

        self.assertEqual(result.refined_query, "Total revenue in Q1 2026 for Claycomo")

    def test_replaces_time_filter(self):
        context = {
            "previous_context": [
                {
                    "query": "Total revenue in Q1 2026 for Dearborn",
                    "refined_query": "Total revenue in Q1 2026 for Dearborn",
                    "response": "$2.3M",
                }
            ],
            "current_query": "What about Q2 2026?",
        }

        result = rewrite_query("What about Q2 2026?", context)

        self.assertEqual(result.refined_query, "Total revenue in Q2 2026 for Dearborn")

    def test_standalone_query_is_not_rewritten(self):
        context = {
            "previous_context": [
                {
                    "query": "Total revenue in Q1 2026",
                    "refined_query": "Total revenue in Q1 2026",
                    "response": "$2.3M",
                }
            ],
            "current_query": "Show production units for Chicago last week",
        }

        result = rewrite_query("Show production units for Chicago last week", context)

        self.assertFalse(result.was_rewritten)
        self.assertEqual(result.refined_query, "Show production units for Chicago last week")

    def test_ambiguous_short_follow_up_requests_clarification(self):
        context = {
            "previous_context": [
                {
                    "query": "Total revenue in Q1 2026",
                    "refined_query": "Total revenue in Q1 2026",
                    "response": "$2.3M",
                }
            ],
            "current_query": "same",
        }

        result = rewrite_query("same", context)

        self.assertTrue(result.needs_clarification)


if __name__ == "__main__":
    unittest.main()
