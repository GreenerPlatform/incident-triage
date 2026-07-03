# Homebrew formula for incident-triage.
#
# This belongs in a tap repo (github.com/GreenerPlatform/homebrew-tap) so users run:
#   brew tap greenerplatform/tap
#   brew install incident-triage
#
# incident-triage is a single stdlib-only Python module, so no vendored resources
# are needed. The `url`/`sha256` point at the PyPI sdist (or a GitHub release tarball).
class IncidentTriage < Formula
  desc "Deterministic Kubernetes incident triage: alert to cause to fix plan"
  homepage "https://github.com/GreenerPlatform/incident-triage"
  url "https://files.pythonhosted.org/packages/source/i/incident-triage/incident_triage-1.2.1.tar.gz"
  sha256 "REPLACE_WITH_SDIST_SHA256"
  license "Apache-2.0"

  depends_on "python@3.12"

  def install
    libexec.install "incident_triage.py"
    (bin/"incident-triage").write <<~SH
      #!/bin/bash
      exec "#{Formula["python@3.12"].opt_bin}/python3" "#{libexec}/incident_triage.py" "$@"
    SH
  end

  test do
    assert_match "incident-triage", shell_output("#{bin}/incident-triage --version")
  end
end
