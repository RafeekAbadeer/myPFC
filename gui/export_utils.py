import os
import csv
import datetime
from PyQt5.QtGui import QPainter, QColor, QFont, QFontMetrics
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QTableView, QHeaderView
from PyQt5.QtCore import Qt, QRect, QSize


def export_table_data(parent, table_view, default_filename=None, export_title=None):
    """
    General function to export data from a table view

    Args:
        parent: Parent widget for dialogs
        table_view: QTableView containing the data to export
        default_filename: Optional default name for the exported file
        export_title: Optional title for the export document
    """
    if not isinstance(table_view, QTableView):
        QMessageBox.warning(parent, "Export Error", "Invalid table view provided for export.")
        return

    model = table_view.model()
    if not model or model.rowCount() == 0:
        QMessageBox.information(parent, "Export Info", "No data to export.")
        return

    # If no export title is provided, try to get one from the window title
    if not export_title:
        window_title = parent.window().windowTitle()
        export_title = f"{window_title} Data"

    # Prepare default filename
    if not default_filename:
        default_filename = f"export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Get file path from user
    file_path, selected_filter = QFileDialog.getSaveFileName(
        parent,
        "Export Data",
        os.path.expanduser(f"~/{default_filename}"),
        "CSV Files (*.csv);;Excel Files (*.xlsx);;PDF Files (*.pdf)"
    )

    if not file_path:
        return  # User canceled

    # Determine export format based on file extension
    if file_path.lower().endswith('.csv'):
        export_to_csv(parent, table_view, file_path)
    elif file_path.lower().endswith('.xlsx'):
        export_to_excel(parent, table_view, file_path)
    elif file_path.lower().endswith('.pdf'):
        export_to_pdf(parent, table_view, file_path, export_title)
    else:
        # Add default extension if none provided
        if "CSV Files" in selected_filter:
            file_path += ".csv"
            export_to_csv(parent, table_view, file_path)
        elif "Excel Files" in selected_filter:
            file_path += ".xlsx"
            export_to_excel(parent, table_view, file_path)
        elif "PDF Files" in selected_filter:
            file_path += ".pdf"
            export_to_pdf(parent, table_view, file_path, export_title)
        else:
            QMessageBox.warning(parent, "Export Error", "Unknown export format.")
            return


def export_to_csv(parent, table_view, file_path):
    """Export table data to CSV file"""
    try:
        model = table_view.model()
        rows = model.rowCount()
        columns = model.columnCount()

        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # Write headers
            headers = []
            for column in range(columns):
                header_text = model.headerData(column, Qt.Horizontal)
                headers.append(header_text if header_text else f"Column {column + 1}")
            writer.writerow(headers)

            # Write data
            for row in range(rows):
                row_data = []
                for column in range(columns):
                    index = model.index(row, column)
                    data = model.data(index)
                    row_data.append(data if data is not None else "")
                writer.writerow(row_data)

        QMessageBox.information(parent, "Export Success", f"Data exported successfully to {file_path}")
    except Exception as e:
        QMessageBox.critical(parent, "Export Error", f"Failed to export to CSV: {str(e)}")

def export_to_excel(parent, table_view, file_path):
    """Export table data to Excel file"""
    try:
        # Try to import openpyxl - will be needed for Excel export
        import openpyxl
        from openpyxl import Workbook

        model = table_view.model()
        rows = model.rowCount()
        columns = model.columnCount()

        wb = Workbook()
        ws = wb.active
        ws.title = "Exported Data"

        # Write headers
        for column in range(columns):
            header_text = model.headerData(column, Qt.Horizontal)
            cell = ws.cell(row=1, column=column + 1)
            cell.value = header_text if header_text else f"Column {column + 1}"
            # Add some styling to headers (optional)
            cell.font = openpyxl.styles.Font(bold=True)

        # Write data
        for row in range(rows):
            for column in range(columns):
                index = model.index(row, column)
                data = model.data(index)
                ws.cell(row=row + 2, column=column + 1, value=data if data is not None else "")

        # Auto-adjust column widths (optional)
        for column in range(columns):
            column_letter = openpyxl.utils.get_column_letter(column + 1)
            max_width = 0
            for row in range(rows + 1):  # +1 to include header
                cell = ws.cell(row=row + 1, column=column + 1)
                if cell.value:
                    max_width = max(max_width, len(str(cell.value)))
            ws.column_dimensions[column_letter].width = max_width + 2  # Add padding

        wb.save(file_path)
        QMessageBox.information(parent, "Export Success", f"Data exported successfully to {file_path}")
    except ImportError:
        QMessageBox.critical(parent, "Export Error",
                             "Excel export requires the openpyxl package.\n"
                             "Please install it with: pip install openpyxl")
    except Exception as e:
        QMessageBox.critical(parent, "Export Error", f"Failed to export to Excel: {str(e)}")


def export_to_pdf(parent, table_view, file_path, title=None):
    """Export table data to PDF file using ReportLab"""
    try:
        # Try to import reportlab - will be needed for PDF export
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.platypus.flowables import Flowable
        from reportlab.pdfgen.canvas import Canvas

        # For page numbers
        from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
        from reportlab.platypus.frames import Frame

        model = table_view.model()
        rows = model.rowCount()
        columns = model.columnCount()

        # Get a more descriptive title if not provided
        if not title:
            title = "Data Export"

        # Create the full title
        full_title = title

        # Get current date and time for the report
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Get headers
        headers = []
        for column in range(columns):
            header_text = model.headerData(column, Qt.Horizontal)
            headers.append(header_text if header_text else f"Column {column + 1}")

        # Get data and calculate column widths based on content
        table_data = []
        styles = getSampleStyleSheet()

        # Create a paragraph style for cells that allows wrapping
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            wordWrap='CJK',  # Use CJK wrapping for better results
            leading=12  # Space between lines
        )

        # Create header style that prevents wrapping
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            wordWrap='LO',  # 'LO' ensures it doesn't wrap
            alignment=1,  # Center alignment
            leading=14
        )

        # Create header row with non-wrapping style
        header_row = []
        for header in headers:
            header_para = Paragraph(f"<b>{header}</b>", header_style)
            header_row.append(header_para)

        table_data.append(header_row)  # Add header row ONLY ONCE

        # Initialize column widths with minimum widths needed for headers
        col_max_widths = []
        for header in headers:
            # More generous spacing for headers to prevent wrapping
            # Shorter headers need proportionally more padding
            header_len = len(str(header))
            if header_len <= 10:  # For shorter headers like Category, Currency, Nature
                # More aggressive padding for short headers
                min_width = header_len * 0.15 * inch + 0.5 * inch
            else:
                # Standard padding for longer headers
                min_width = header_len * 0.12 * inch + 0.3 * inch
            col_max_widths.append(min_width)

        # Process data rows - allow content to expand column width if needed
        for row in range(rows):
            row_data = []
            for column in range(columns):
                index = model.index(row, column)
                data = model.data(index)
                cell_value = data if data is not None else ""

                # Special handling for columns that need wrapping
                if headers[column] in ['Credit Accounts', 'Debit Accounts', 'Description', 'Classifications']:
                    # Create paragraph for cell to enable wrapping
                    cell_para = Paragraph(str(cell_value).replace('\n', '<br/>'), cell_style)
                    row_data.append(cell_para)

                    # Update max width - approximately measure text
                    content_lines = str(cell_value).split('\n')
                    max_line_length = max(len(line) for line in content_lines) if content_lines else 0
                    content_width = max_line_length * 0.1 * inch
                    col_max_widths[column] = max(col_max_widths[column], content_width)
                else:
                    # For regular text, create a non-wrapping paragraph to ensure content stays in its column
                    if len(str(cell_value)) > 20:  # Only wrap very long content
                        cell_para = Paragraph(str(cell_value), cell_style)
                        row_data.append(cell_para)
                    else:
                        # Use plain strings for short content to prevent spillover
                        row_data.append(str(cell_value))

                    # Update max width and ensure enough space for content
                    content_width = len(str(cell_value)) * 0.12 * inch + 0.1 * inch  # Add small padding
                    col_max_widths[column] = max(col_max_widths[column], content_width)

            table_data.append(row_data)

        # Determine if we need landscape mode by analyzing data
        # Calculate average content width
        total_estimated_width = sum(width for width in col_max_widths) + (0.2 * inch * columns)  # Add spacing

        # A4 sizes: 8.27 x 11.69 inches
        portrait_width = 8.27 * 0.8  # Leave margins

        # Use landscape if content is too wide for portrait
        use_landscape = total_estimated_width > portrait_width
        page_size = landscape(A4) if use_landscape else A4

        # Create a custom document template with header and footer
        class MyDocTemplate(BaseDocTemplate):
            def __init__(self, filename, **kw):
                self.allowSplitting = 0
                BaseDocTemplate.__init__(self, filename, **kw)
                template = PageTemplate('normal', [Frame(
                    self.leftMargin, self.bottomMargin, self.width, self.height, id='normal'
                )])
                self.addPageTemplates([template])

            def afterPage(self):
                self.canv.saveState()
                # Add footer with page numbers and timestamp
                self.canv.setFont('Helvetica', 8)
                footer_text = f"Page {self.canv.getPageNumber()} - Generated: {current_time}"
                self.canv.drawRightString(
                    self.width + self.leftMargin,
                    0.5 * inch,
                    footer_text
                )
                self.canv.restoreState()

        # Create the PDF document
        doc = MyDocTemplate(
            file_path,
            pagesize=page_size,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch
        )

        # Create a list of flowables for the document
        elements = []

        # Add title
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        elements.append(Paragraph(full_title, title_style))
        elements.append(Spacer(1, 0.25 * inch))

        # Calculate column widths based on content
        available_width = doc.width
        min_col_width = 0.4 * inch

        # Adjust column widths to fit available space
        col_widths = []
        for width in col_max_widths:
            # Ensure minimum width
            w = max(width, min_col_width)
            col_widths.append(w)

        # Check if total width exceeds available width
        total_width = sum(col_widths)
        if total_width > available_width:
            # Scale down proportionally
            scale = available_width / total_width
            col_widths = [w * scale for w in col_widths]

        # Make the table with calculated widths
        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        # Style the table
        style = TableStyle([
            # Header formatting
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),

            # Body formatting
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Align text to top for better wrapping

            # Right align numeric columns
            ('ALIGN', (0, 1), (0, -1), 'RIGHT'),  # ID column
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),  # Amount column

            # Left align text columns
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),  # Description
            ('ALIGN', (5, 1), (6, -1), 'LEFT'),  # Credit/Debit accounts

            # Table grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),

            # Zebra stripes for rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ])

        table.setStyle(style)
        elements.append(table)

        # Build the PDF
        doc.build(elements)

        QMessageBox.information(parent, "Export Success", f"Data exported successfully to {file_path}")
    except ImportError:
        QMessageBox.critical(parent, "Export Error",
                             "PDF export requires the reportlab package.\n"
                             "Please install it with: pip install reportlab")
    except Exception as e:
        QMessageBox.critical(parent, "Export Error", f"Failed to export to PDF: {str(e)}")

def is_numeric(text):
    """Check if a string represents a numeric value"""
    try:
        float(text)
        return True
    except (ValueError, TypeError):
        return False