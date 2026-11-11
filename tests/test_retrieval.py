import unittest

from agents.retrieval import retrieve


class RetrievalTests(unittest.TestCase):
    def test_retriever_ranks_pip_reference_for_pip_question(self):
        docs = retrieve("Comment calculer la valeur d’un pip EUR/USD et d’une pipette ?")
        self.assertGreaterEqual(len(docs), 1)
        self.assertEqual(docs[0]["id"], "pip-basics")
        self.assertTrue(docs[0]["source_url"].startswith("https://"))

    def test_retriever_returns_adx_source_and_caps_document_count(self):
        docs = retrieve("ADX force tendance, direction +DI -DI ?", limit=2)
        self.assertEqual(docs[0]["id"], "adx-strength")
        self.assertLessEqual(len(docs), 2)

    def test_empty_or_unrelated_query_returns_no_documents(self):
        self.assertEqual(retrieve("et de la ?"), [])
        self.assertEqual(retrieve("volcan martien fromage"), [])


if __name__ == "__main__":
    unittest.main()
