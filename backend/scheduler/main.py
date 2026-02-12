"""分析スケジューラー。

定期実行で分析層の判定フローを起動する。
開発フェーズでは手動トリガーも可能。

TODO: Step 3 で実装
"""

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("Scheduler started (not yet implemented)")
    # TODO: 定期実行ループの実装


if __name__ == "__main__":
    main()
