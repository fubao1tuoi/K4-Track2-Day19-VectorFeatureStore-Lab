"""Five-query demonstration for HybridMemoryAgent."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from bonus.agent import HybridMemoryAgent  # noqa: E402


def main() -> int:
    agent = HybridMemoryAgent(top_k=3)
    memories = [
        "Tôi đã đọc tài liệu Kubernetes về Deployment, Service và cách rolling update an toàn.",
        "Ghi chú cloud: autoscaling tự động mở rộng hạ tầng theo CPU và lưu lượng người dùng.",
        "Tài liệu AWS khuyên dùng spot instance và budget alert để giảm chi phí cloud.",
        "Tôi học OAuth 2.0, JWT và nguyên tắc zero trust để bảo vệ API nội bộ.",
        "Cloud security cần mã hóa dữ liệu, phân quyền tối thiểu và xoay vòng secrets.",
        "Tôi thích bài viết kỹ thuật ngắn, có ví dụ thực hành và checklist triển khai.",
    ]
    for memory in memories:
        agent.remember(memory, user_id="u_001")

    # A second user's secret proves that every retrieval call is tenant-filtered.
    agent.remember("Bí mật của user khác: dự án Mặt Trăng.", user_id="u_999")

    queries = [
        "Tôi đã đọc gì về Kubernetes?",
        "Recommend đọc gì tiếp",
        "Tôi đang quan tâm gì gần đây?",
        "Tài liệu về tự động mở rộng hạ tầng?",
        "Cho tôi summary cloud security",
    ]
    for number, query in enumerate(queries, 1):
        print(f"\n{'=' * 18} QUERY {number} {'=' * 18}")
        print(agent.recall(query, user_id="u_001"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
