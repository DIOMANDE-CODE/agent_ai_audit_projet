"""
Génération de rapports PDF stylisés à partir des rapports d'audit Markdown.
Utilise ReportLab — pure Python, aucune dépendance système externe.
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def generer_pdf(contenu_md: str, chemin_md: Path) -> Path:
    """
    Génère un rapport PDF stylisé à partir du contenu Markdown de l'audit.

    Le PDF est sauvegardé dans le même dossier que le fichier .md,
    avec le même nom de base et l'extension .pdf.

    Args:
        contenu_md: Contenu Markdown brut retourné par Gemini.
        chemin_md:  Chemin du fichier .md déjà sauvegardé.

    Returns:
        Chemin du fichier PDF généré.

    Raises:
        ImportError: Si reportlab n'est pas installé.
        Exception:   Si la génération PDF échoue.
    """
    try:
        from reportlab.lib.colors import HexColor, white          # type: ignore[import-untyped]
        from reportlab.lib.enums import TA_CENTER                  # type: ignore[import-untyped]
        from reportlab.lib.pagesizes import A4                     # type: ignore[import-untyped]
        from reportlab.lib.styles import ParagraphStyle            # type: ignore[import-untyped]
        from reportlab.lib.units import cm                         # type: ignore[import-untyped]
        from reportlab.platypus import (                           # type: ignore[import-untyped]
            HRFlowable,
            PageBreak,
            Paragraph,
            Preformatted,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as e:
        raise ImportError(
            "ReportLab n'est pas installé.\n"
            "Exécutez : pip install reportlab"
        ) from e

    # ── Dimensions ────────────────────────────────────────────────────────────
    MARGE_H     = 1.8 * cm
    MARGE_V_H   = 2.0 * cm
    MARGE_V_B   = 2.8 * cm
    LARGEUR     = A4[0] - 2 * MARGE_H

    # ── Palette de couleurs ───────────────────────────────────────────────────
    C_TITRE_FOND    = HexColor('#1a365d')
    C_BLOC_FOND     = HexColor('#2b6cb0')
    C_H3_BORDURE    = HexColor('#4299e1')
    C_H4_FOND       = HexColor('#edf2f7')
    C_CODE_FOND     = HexColor('#1a202c')
    C_CODE_TEXTE    = HexColor('#e2e8f0')
    C_BQ_FOND       = HexColor('#ebf8ff')
    C_BQ_BORDURE    = HexColor('#4299e1')
    C_TEXTE         = HexColor('#2d3748')
    C_TEXTE_FORT    = HexColor('#1a365d')
    C_SEP           = HexColor('#e2e8f0')
    C_PIED_LABEL    = HexColor('#a0aec0')
    C_PIED_PAGE     = HexColor('#718096')

    # ── Styles typographiques ─────────────────────────────────────────────────
    S_H1 = ParagraphStyle(
        'H1', fontName='Helvetica-Bold', fontSize=17,
        textColor=white, alignment=TA_CENTER,
        spaceAfter=0, spaceBefore=0,
    )
    S_H2 = ParagraphStyle(
        'H2', fontName='Helvetica-Bold', fontSize=11.5,
        textColor=white, spaceAfter=0, spaceBefore=0,
    )
    S_H3 = ParagraphStyle(
        'H3', fontName='Helvetica-Bold', fontSize=10.5,
        textColor=C_TEXTE_FORT, spaceAfter=4, spaceBefore=10,
    )
    S_H4 = ParagraphStyle(
        'H4', fontName='Helvetica-Bold', fontSize=10,
        textColor=C_TEXTE, spaceAfter=0, spaceBefore=0,
    )
    S_CORPS = ParagraphStyle(
        'Corps', fontName='Helvetica', fontSize=9.5,
        textColor=C_TEXTE, leading=14, spaceAfter=5,
    )
    S_PUCE = ParagraphStyle(
        'Puce', fontName='Helvetica', fontSize=9.5,
        textColor=C_TEXTE, leading=14, spaceAfter=2,
        leftIndent=16, bulletIndent=4,
        bulletFontName='Helvetica', bulletFontSize=10,
    )
    S_NUM = ParagraphStyle(
        'Num', fontName='Helvetica', fontSize=9.5,
        textColor=C_TEXTE, leading=14, spaceAfter=2,
        leftIndent=20, firstLineIndent=-14,
    )
    S_CODE = ParagraphStyle(
        'Code', fontName='Courier', fontSize=7.5,
        textColor=C_CODE_TEXTE, leading=11,
        spaceAfter=0, spaceBefore=0,
    )
    S_BQ = ParagraphStyle(
        'BQ', fontName='Helvetica', fontSize=9,
        textColor=HexColor('#2c5282'), leading=13,
        spaceAfter=0, spaceBefore=0,
    )

    # ── Formatage inline Markdown → XML ReportLab ─────────────────────────────

    def formater_inline(texte: str) -> str:
        """Convertit le Markdown inline en markup XML compatible ReportLab."""
        # Protéger les segments de code inline avant l'échappement XML
        codes: list[str] = []

        def _extraire_code(m: re.Match) -> str:
            codes.append(m.group(1))
            return f'\x00CODE{len(codes) - 1}\x00'

        texte = re.sub(r'`([^`\n]+)`', _extraire_code, texte)

        # Échapper les caractères XML du texte brut
        texte = texte.replace('&', '&amp;')
        texte = texte.replace('<', '&lt;')
        texte = texte.replace('>', '&gt;')

        # Statut global coloré : **Statut global :** <STATUT>
        _COULEURS_STATUT: dict[str, str] = {
            'BON':            '#22543d',
            'ACCEPTABLE':     '#1a365d',
            'INSUFFISANT':    '#7b341e',
            'CRITIQUE':       '#742a2a',
            'NON APPLICABLE': '#4a5568',
            'NON ÉVALUÉ':     '#4a5568',
            'NON EVALUÉ':     '#4a5568',
        }

        def _rempl_statut(m: re.Match) -> str:
            s = m.group(1)
            c = _COULEURS_STATUT.get(s, '#4a5568')
            return f'<b>Statut global :</b> <font color="{c}"><b>{s}</b></font>'

        texte = re.sub(
            r'\*\*Statut global\s*:\*\*\s*'
            r'(BON|ACCEPTABLE|INSUFFISANT|CRITIQUE|NON APPLICABLE|NON ÉVALUÉ|NON EVALUÉ)',
            _rempl_statut, texte,
        )

        # Badges de risque
        _BADGES: dict[str, str] = {
            '[CRITIQUE]': '<font color="#742a2a"><b>[CRITIQUE]</b></font>',
            '[ELEVE]':    '<font color="#7b341e"><b>[ELEVE]</b></font>',
            '[MOYEN]':    '<font color="#744210"><b>[MOYEN]</b></font>',
            '[FAIBLE]':   '<font color="#1a365d"><b>[FAIBLE]</b></font>',
            '[INFO]':     '<font color="#4a5568">[INFO]</font>',
        }
        for badge, html in _BADGES.items():
            texte = texte.replace(badge, html)

        # Note globale mise en valeur
        texte = re.sub(
            r'\*\*NOTE GLOBALE\s*:\s*([^*]+)\*\*',
            r'<font color="#1a365d" size="13"><b>NOTE GLOBALE : \1</b></font>',
            texte,
        )

        # Gras : **text** → <b>text</b>
        texte = re.sub(r'\*\*([^*\n]+)\*\*', r'<b>\1</b>', texte)

        # Italique : *text* → <i>text</i>
        texte = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<i>\1</i>', texte)

        # Restaurer les codes inline avec style monospace
        for idx, code in enumerate(codes):
            safe = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            texte = texte.replace(
                f'\x00CODE{idx}\x00',
                f'<font name="Courier" size="8.5" color="#c53030">{safe}</font>',
            )

        return texte

    # ── Constructeurs d'éléments ──────────────────────────────────────────────

    def _table_fond(para: Paragraph, fond, bordure_gauche: tuple | None = None,
                    pad: tuple[int, int, int, int] = (14, 10, 14, 10)) -> Table:
        t = Table([[para]], colWidths=[LARGEUR])
        style_cmds: list = [
            ('TOPPADDING',    (0, 0), (-1, -1), pad[1]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), pad[3]),
            ('LEFTPADDING',   (0, 0), (-1, -1), pad[0]),
            ('RIGHTPADDING',  (0, 0), (-1, -1), pad[2]),
        ]
        if fond is not None:
            style_cmds.append(('BACKGROUND', (0, 0), (-1, -1), fond))
        if bordure_gauche:
            epaisseur, couleur = bordure_gauche
            style_cmds.append(('LINEBEFORE', (0, 0), (0, -1), epaisseur, couleur))
        t.setStyle(TableStyle(style_cmds))
        return t

    def el_h1(texte: str) -> Table:
        p = Paragraph(formater_inline(texte), S_H1)
        return _table_fond(p, C_TITRE_FOND, pad=(14, 22, 14, 22))

    def el_h2(texte: str) -> Table:
        p = Paragraph(formater_inline(texte), S_H2)
        return _table_fond(p, C_BLOC_FOND, pad=(14, 10, 14, 10))

    def el_h3(texte: str) -> Table:
        p = Paragraph(formater_inline(texte), S_H3)
        return _table_fond(p, None,
                           bordure_gauche=(4, C_H3_BORDURE),
                           pad=(10, 5, 0, 5))

    def el_h4(texte: str) -> Table:
        p = Paragraph(formater_inline(texte), S_H4)
        return _table_fond(p, C_H4_FOND,
                           bordure_gauche=(5, C_H3_BORDURE),
                           pad=(12, 7, 8, 7))

    def el_code(code: str) -> list:
        # ReportLab ne peut pas couper une Table à 1 cellule entre deux pages.
        # Limite : (frame_height 693pt - padding 20pt) / leading 11pt ≈ 61 lignes.
        # On prend 55 pour laisser une marge de sécurité.
        MAX_LIGNES = 55
        _style = TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), C_CODE_FOND),
            ('TOPPADDING',    (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING',   (0, 0), (-1, -1), 12),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
        ])
        lignes = code.split('\n')
        tables = []
        for i in range(0, max(len(lignes), 1), MAX_LIGNES):
            pre = Preformatted('\n'.join(lignes[i:i + MAX_LIGNES]), S_CODE)
            t = Table([[pre]], colWidths=[LARGEUR])
            t.setStyle(_style)
            tables.append(t)
        return tables

    def el_blockquote(texte: str) -> Table:
        p = Paragraph(formater_inline(texte), S_BQ)
        return _table_fond(p, C_BQ_FOND,
                           bordure_gauche=(4, C_BQ_BORDURE),
                           pad=(12, 8, 8, 8))

    def el_para(texte: str) -> Paragraph:
        return Paragraph(formater_inline(texte), S_CORPS)

    def el_puce(texte: str) -> Paragraph:
        return Paragraph(formater_inline(texte), S_PUCE, bulletText='•')

    def el_num(num: int, texte: str) -> Paragraph:
        return Paragraph(f'{num}. {formater_inline(texte)}', S_NUM)

    def el_sep() -> HRFlowable:
        return HRFlowable(
            width='100%', thickness=0.5,
            color=C_SEP, spaceAfter=6, spaceBefore=6,
        )

    # ── Détection de début de bloc ────────────────────────────────────────────

    def _est_debut_bloc(ligne: str) -> bool:
        return (
            ligne.startswith('#') or
            ligne.startswith('```') or
            ligne.startswith('> ') or
            ligne.startswith('- ') or
            ligne.startswith('* ') or
            bool(re.match(r'^\d+\. ', ligne)) or
            ligne.strip() == '---'
        )

    # ── Parser Markdown ────────────────────────────────────────────────────────

    def _parser() -> list:
        elements: list = []
        lignes = contenu_md.split('\n')
        i = 0
        premier_h2 = True

        while i < len(lignes):
            ligne = lignes[i]

            # H1
            if ligne.startswith('# ') and not ligne.startswith('## '):
                elements.append(el_h1(ligne[2:].strip()))
                elements.append(Spacer(1, 10))
                i += 1

            # H2 — chaque BLOC commence sur une nouvelle page (sauf le premier)
            elif ligne.startswith('## '):
                if not premier_h2:
                    elements.append(PageBreak())
                elements.append(el_h2(ligne[3:].strip()))
                elements.append(Spacer(1, 8))
                premier_h2 = False
                i += 1

            # H3
            elif ligne.startswith('### '):
                elements.append(el_h3(ligne[4:].strip()))
                elements.append(Spacer(1, 4))
                i += 1

            # H4
            elif ligne.startswith('#### '):
                elements.append(el_h4(ligne[5:].strip()))
                elements.append(Spacer(1, 3))
                i += 1

            # Bloc de code (```)
            elif ligne.startswith('```'):
                code_lignes: list[str] = []
                i += 1
                while i < len(lignes) and not lignes[i].startswith('```'):
                    code_lignes.append(lignes[i])
                    i += 1
                if i < len(lignes):
                    i += 1  # dépasser le ``` de fermeture
                if code_lignes:
                    elements.extend(el_code('\n'.join(code_lignes)))
                    elements.append(Spacer(1, 6))

            # Blockquote
            elif ligne.startswith('> '):
                bq: list[str] = []
                while i < len(lignes) and lignes[i].startswith('> '):
                    bq.append(lignes[i][2:])
                    i += 1
                elements.append(el_blockquote(' '.join(bq)))
                elements.append(Spacer(1, 4))

            # Séparateur horizontal
            elif ligne.strip() == '---':
                elements.append(el_sep())
                i += 1

            # Liste à puces (- ou *)
            elif ligne.startswith('- ') or ligne.startswith('* '):
                while i < len(lignes) and (lignes[i].startswith('- ') or lignes[i].startswith('* ')):
                    elements.append(el_puce(lignes[i][2:]))
                    i += 1
                elements.append(Spacer(1, 4))

            # Liste numérotée
            elif re.match(r'^\d+\. ', ligne):
                num = 0
                while i < len(lignes) and re.match(r'^\d+\. ', lignes[i]):
                    num += 1
                    texte_item = re.sub(r'^\d+\. ', '', lignes[i])
                    elements.append(el_num(num, texte_item))
                    i += 1
                elements.append(Spacer(1, 4))

            # Ligne vide
            elif not ligne.strip():
                elements.append(Spacer(1, 3))
                i += 1

            # Paragraphe : accumule les lignes contiguës non-bloc
            else:
                para_lignes: list[str] = []
                while i < len(lignes) and lignes[i].strip() and not _est_debut_bloc(lignes[i]):
                    para_lignes.append(lignes[i])
                    i += 1
                if para_lignes:
                    elements.append(el_para(' '.join(para_lignes)))

        return elements

    # ── Pied de page ──────────────────────────────────────────────────────────

    def _footer(canvas_obj, _doc):
        canvas_obj.saveState()
        y = MARGE_V_B - 1.1 * cm
        # Ligne de séparation
        canvas_obj.setStrokeColor(C_SEP)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(MARGE_H, y + 0.35 * cm, A4[0] - MARGE_H, y + 0.35 * cm)
        canvas_obj.setFont('Helvetica', 7.5)
        # Label à gauche
        canvas_obj.setFillColor(C_PIED_LABEL)
        canvas_obj.drawString(MARGE_H, y, "CONFIDENTIEL — Rapport d'Audit Technique")
        # Numéro de page à droite
        canvas_obj.setFillColor(C_PIED_PAGE)
        canvas_obj.drawRightString(
            A4[0] - MARGE_H, y,
            f"Page {canvas_obj._pageNumber}",
        )
        canvas_obj.restoreState()

    # ── Construction du PDF ────────────────────────────────────────────────────

    chemin_pdf = chemin_md.with_suffix('.pdf')

    doc = SimpleDocTemplate(
        str(chemin_pdf),
        pagesize=A4,
        leftMargin=MARGE_H,
        rightMargin=MARGE_H,
        topMargin=MARGE_V_H,
        bottomMargin=MARGE_V_B,
    )

    logger.info("Generation du PDF en cours...")
    doc.build(_parser(), onFirstPage=_footer, onLaterPages=_footer)

    taille_ko = chemin_pdf.stat().st_size / 1024
    logger.info("PDF genere : %s (%.0f Ko)", chemin_pdf.name, taille_ko)

    return chemin_pdf
