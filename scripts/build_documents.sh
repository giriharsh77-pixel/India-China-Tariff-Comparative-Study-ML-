#!/usr/bin/env bash
# Rebuild report, viva Q&A, data dictionary, notebooks and slide deck from the pipeline outputs.
# PDF export uses Microsoft Word / Keynote on macOS (optional; skipped elsewhere).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/export_results.py
python3 scripts/make_data_dictionary.py
python3 scripts/update_readme.py
python3 scripts/build_report.py
python3 scripts/build_viva.py
python3 scripts/make_notebooks.py
( cd presentation && node build_deck.js )
if [[ "$(uname)" == "Darwin" ]]; then
  osascript -e "with timeout of 600 seconds
tell application \"Microsoft Word\"
  open (POSIX file \"$PWD/docs/report.docx\")
  delay 3
  save as active document file name \"$PWD/docs/report.pdf\" file format format PDF
  close active document saving no
end tell
end timeout" || echo "Word PDF export skipped"
  osascript -e "with timeout of 600 seconds
tell application \"Keynote\"
  set d to open (POSIX file \"$PWD/presentation/presentation.pptx\")
  delay 5
  export d to (POSIX file \"$PWD/presentation/presentation.pdf\") as PDF
  close d saving no
end tell
end timeout" || echo "Keynote PDF export skipped"
fi
echo "documents rebuilt"
