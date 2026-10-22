import unittest
from codex_transport import command, DISABLED


class TransportTests(unittest.TestCase):
    def test_supplied_prompt_only_without_old_workspace_or_history(self):
        result = command(["--sandbox", "read-only", "--ask-for-approval", "never", "--search",
                          "exec", "--model", "gpt-6.1-sol", "-c", 'model_reasoning_effort="xhigh"',
                          "--json", "--skip-git-repo-check", "-"], "/empty/request")
        self.assertNotIn("--search", result)
        self.assertIn("--ignore-user-config", result)
        self.assertIn("project_doc_max_bytes=0", result)
        self.assertIn('web_search="disabled"', result)
        self.assertIn("/empty/request", result)
        self.assertIn("gpt-6.1-sol", result)
        for feature in DISABLED:
            self.assertIn(f"features.{feature}=false", result)
        for args in (["exec", "resume", "abc"], ["exec", "fork"], ["login"]):
            with self.assertRaises(ValueError):
                command(args, "/empty/request")

    def test_subscription_status_passthrough_does_not_start_model(self):
        self.assertEqual(command(["login", "status"], "/unused")[1:], ["login", "status"])


if __name__ == "__main__":
    unittest.main()
