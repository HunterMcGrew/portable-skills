# Sage — non-Markdown document generation

Fires only when the user asks for a shareable document beyond Markdown. Markdown itself is the default and lives in `SKILL.md` § Document generation — this file covers .docx, PDF, and Google Docs only.

Non-Markdown formats save beside the Markdown destination (same directory, same `<old-tag>-<new-tag>` stem). Create the directory on first write.

- **.docx (on request):** generate with the `docx` npm package — title as Heading 1 ("Release Notes: \<old-tag\> → \<new-tag\>"), date subtitle, category headers as Heading 2 with counts, bulleted entries with the ticket bold and the PR number as an external hyperlink, US Letter, 1-inch margins, Arial. Use the package's bullet numbering config, never unicode bullets.
- **PDF (on request):** generate the .docx first, then convert headlessly with LibreOffice (`soffice --headless --convert-to pdf <file>.docx`).
- **Google Docs (on request, when connected):** create the doc via the connected tool, format headings and bullets, share the URL.

If .docx generation fails during delivery, offer PDF or Markdown; Markdown is the final failsafe — plain text always works.
