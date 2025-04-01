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
        table_data = [headers]  # Start with headers
        col_max_widths = [len(str(h)) for h in headers]  # Track max width of each column

        for row in range(rows):
            row_data = []
            for column in range(columns):
                index = model.index(row, column)
                data = model.data(index)
                cell_value = data if data is not None else ""
                row_data.append(cell_value)

                # Update maximum column width
                col_max_widths[column] = max(col_max_widths[column], len(str(cell_value)))

            table_data.append(row_data)

        # Determine if we need landscape mode by analyzing data
        # Calculate average content width
        avg_char_width = 0.08 * inch  # Approximate width per character
        total_estimated_width = sum(width * avg_char_width for width in col_max_widths) + (
                    0.5 * inch * columns)  # Add spacing

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

        # Create table
        table = Table(table_data)

        # Style the table
        style = TableStyle([
            # Header formatting
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),

            # Body formatting
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),

            # Alignment for numeric columns (this is generic, can be refined)
            # Number columns are right-aligned
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            # Text columns are left-aligned
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),

            # Table grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),

            # Zebra stripes for rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ])

        # Apply specific numeric column detection
        # Check multiple data rows to determine if columns are numeric
        num_rows_to_check = min(5, rows)
        for col in range(columns):
            numeric_count = 0

            for row_idx in range(num_rows_to_check):
                if row_idx >= rows:
                    break

                index = model.index(row_idx, col)
                cell_value = model.data(index)

                # If it's numeric, increment counter
                if is_numeric(str(cell_value)):
                    numeric_count += 1

            # If majority of checked cells are numeric, keep right alignment
            # Otherwise switch to left alignment
            if numeric_count <= num_rows_to_check / 2:
                style.add('ALIGN', (col, 1), (col, -1), 'LEFT')

        table.setStyle(style)

        # Calculate column widths based on content
        available_width = doc.width
        min_col_width = 0.4 * inch

        # Convert character counts to inches with padding
        col_widths = []
        for width in col_max_widths:
            # Convert character count to inches (approximate)
            w = width * avg_char_width + 0.3 * inch  # Add padding
            w = max(w, min_col_width)  # Ensure minimum width
            col_widths.append(w)

        # Check if total width exceeds available width
        total_width = sum(col_widths)
        if total_width > available_width:
            # Scale down proportionally
            scale = available_width / total_width
            col_widths = [w * scale for w in col_widths]

        # Make the table with calculated widths
        auto_width_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        auto_width_table.setStyle(style)

        elements.append(auto_width_table)

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