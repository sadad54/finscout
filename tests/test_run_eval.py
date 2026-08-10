import json
from unittest.mock import patch

from app.eval.run_eval import _avg, run_eval


@patch("app.eval.run_eval.judge_report")
@patch("app.eval.run_eval.gather_evidence_and_report")
def test_run_eval_writes_scorecard_and_averages(mock_gather, mock_judge, tmp_path):
    mock_gather.return_value = ({"market_data": {}}, {"overview": "..."})
    mock_judge.return_value = {"faithfulness": 4, "completeness": 5, "groundedness": 3, "reasoning": "ok"}

    with patch("app.eval.run_eval.SCORECARD_DIR", tmp_path):
        summary = run_eval()

    assert summary["avg_faithfulness"] == 4.0
    assert summary["avg_completeness"] == 5.0
    assert summary["avg_groundedness"] == 3.0

    written_files = list(tmp_path.glob("scorecard_*.json"))
    assert len(written_files) == 1
    saved = json.loads(written_files[0].read_text())
    assert saved["num_cases"] == summary["num_cases"]


def test_avg_handles_missing_key():
    scores = [{"faithfulness": 4}, {"faithfulness": 2}, {"other": 1}]
    assert _avg(scores, "faithfulness") == 3.0
    assert _avg(scores, "completeness") is None