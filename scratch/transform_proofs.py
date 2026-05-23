"""
Transform sections/7_postponed_proofs.tex so that individual proof sub-headings
become named \begin{proof}[Proof of ...] environments instead of \subsection{}.
Major subsections ("Proofs for Section 3/4") are kept as subsections.
"""
import re

with open('sections/7_postponed_proofs.tex', 'r', encoding='utf-8') as f:
    content = f.read()

# ------------------------------------------------------------------ helpers
def extract_balanced(text, start):
    """Given text[start] == '{', return (inner_content, end_index_exclusive)."""
    assert text[start] == '{'
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start+1:i], i+1
    raise ValueError("Unbalanced braces")

# ------------------------------------------------------------------ transform
def transform(content):
    result = []
    i = 0

    while i < len(content):
        idx = content.find('\\subsection{', i)
        if idx == -1:
            result.append(content[i:])
            break

        # --- extract balanced title ------------------------------------------
        brace_pos = idx + len('\\subsection')   # points to '{'
        title, after_title = extract_balanced(content, brace_pos)

        # after_title is the index just after the closing '}'
        rest = content[after_title:]

        # --- is the next meaningful content \label{...} + \begin{proof}? ------
        label_match = re.match(
            r'(\r?\n)\\label\{([^}]+)\}(\r?\n)\\begin\{proof\}',
            rest
        )

        # Also guard against the two "major" subsections we want to keep
        is_major = (
            'Proofs for Section 3' in title
            or 'Proofs for Section 4' in title
        )

        if label_match and not is_major:
            # This is an individual proof subsection → convert it
            label     = label_match.group(2)
            after_match = after_title + label_match.end()

            result.append(content[i:idx])   # text before \subsection
            result.append(
                f'\\phantomsection\n'
                f'\\label{{{label}}}\n'
                f'\\begin{{proof}}[{title}]'
            )
            i = after_match
        else:
            # Keep the subsection as-is
            result.append(content[i:after_title])
            i = after_title

    return ''.join(result)

new_content = transform(content)

# ------------------------------------------------------------------ fix intro text
# Update the brief intro under each major subsection so it is 1-2 lines
regression_intro = (
    '\\subsection{Proofs for Section 3 (Regression)}\n'
    '\\label{subsec:proofs_regression}\n\n'
    'The following proofs establish the game-theoretic foundations, offline '
    'generalization bounds, and online regret guarantees for the continuous '
    'regression setting.\n\n'
)

classification_intro = (
    '\\subsection{Proofs for Section 4 (Classification)}\n'
    '\\label{subsec:proofs_classification}\n\n'
    'The following proofs establish the corresponding results for the discrete '
    'multiclass classification setting.\n\n'
)

# Replace the existing major subsection + existing (possibly empty) paragraph
new_content = re.sub(
    r'\\subsection\{Proofs for Section 3 \(Regression\)\}\r?\n'
    r'\\label\{subsec:proofs_regression\}\r?\n(\r?\n)?',
    lambda m: regression_intro,
    new_content
)
new_content = re.sub(
    r'\\subsection\{Proofs for Section 4 \(Classification\)\}\r?\n'
    r'\\label\{subsec:proofs_classification\}\r?\n(\r?\n)?',
    lambda m: classification_intro,
    new_content
)

# ------------------------------------------------------------------ write out
with open('sections/7_postponed_proofs.tex', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Transform complete!')

# Quick sanity check – count \begin{proof} occurrences
proofs_count = new_content.count('\\begin{proof}')
subsection_proofs = len(re.findall(r'\\subsection\{Proof of', new_content))
print(f'  \\begin{{proof}} blocks: {proofs_count}')
print(f'  Remaining \\subsection{{Proof of...}}: {subsection_proofs}  (should be 0)')
