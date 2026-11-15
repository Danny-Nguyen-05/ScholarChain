B3b method decision (session record)
Runbook B3b needs the user's own admin identity; none exists. Coordinator offered: terminal method through a narrow IAM window (inline policy secretsmanager:PutSecretValue and DescribeSecret on arn:aws:secretsmanager:us-east-2:<acct>:secret:scholarchain-course/* plus the same-device CLI login policy on scholarchain-billing-operator, removed afterwards), or the console as root.
User decision in chat, verbatim, 2026-11-13T18:49:17Z: "terminal"
Keys created by the user in the Anthropic Console and the Voyage dashboard (name scholarchain-course-session), stored only in the user's password manager.
B3b result: put-secret-value printed both names; describe-secret shows one AWSCURRENT version for scholarchain-course/anthropic-api-key and scholarchain-course/voyage-api-key (no value read).
B3b IAM window closed: user in chat, verbatim, "removed at 12:56" (local; scholarchain-operator-b3b-keys and scholarchain-operator-cli-login removed).
