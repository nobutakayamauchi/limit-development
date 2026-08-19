from __future__ import annotations
from pathlib import Path
import subprocess
from ..core import Evidence

class GitHubGitAdapter:
    """Deterministic git-history input adapter. Commit SHA is the source_id."""
    def __init__(self, repo_path='.', lookback_days=30, max_commits=200):
        self.repo_path = Path(repo_path)
        self.lookback_days = lookback_days
        self.max_commits = max_commits

    def collect(self):
        fmt = '%H%x1f%cI%x1f%an%x1f%s%x1f%D'
        cmd = ['git','-C',str(self.repo_path),'log',f'--since={self.lookback_days}.days',f'--max-count={self.max_commits}',f'--pretty=format:{fmt}']
        out = subprocess.check_output(cmd, text=True, encoding='utf-8')
        items = []
        for line in out.splitlines():
            if not line.strip(): continue
            parts = line.split('\x1f'); parts += [''] * (5 - len(parts))
            sha, captured_at, actor, subject, refs = parts[:5]
            items.append(Evidence(source_id=sha,captured_at=captured_at,actor=actor,text=subject,source_type='github_commit',raw_evidence_ref=f'commit:{sha}'))
        return items
