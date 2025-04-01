import os
import csv
import datetime
from PyQt5.QtGui import QPainter, QColor, QFont, QFontMetrics
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QTableView, QHeaderView
from PyQt5.QtCore import Qt, QRect, QSize

def export_table_data(parent, table_view, default_filename=None):
    """
    General function to export data from a table view

    Args:
        parent: Parent widget for dialogs
        table_view: QTableView containing the data to export
        default_filename: Optional default name for the exported file
    """
    if not isinstance(table_view, QTableView):
        QMessageBox.warning(parent, "Export Error", "Invalid table view provided for export.")
        return

    model = table_view.model()
    if not model or model.rowCount() == 0:
        QMessageBox.information(parent, "Export Info", "No data to export.")
        return
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
    """Export table data to PDF file with improved formatting"""
    try:
        model = table_view.model()
        rows = model.rowCount()
        columns = model.columnCount()

        # Get a more descriptive title if not provided
        if not title:
            # Try to determine what kind of data we're exporting
            window_title = parent.window().windowTitle()
            title = f"{window_title} - Exported Data"

        # Set up the printer
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(file_path)

        # Calculate total content width to determine orientation
        font_metrics = QFontMetrics(QFont("Arial", 10))
        total_width = 0

        for column in range(columns):
            header_text = model.headerData(column, Qt.Horizontal) or f"Column {column + 1}"
            col_width = font_metrics.horizontalAdvance(header_text) + 20

            # Sample a few rows to estimate width needed
            for row in range(min(10, rows)):
                index = model.index(row, column)
                data = str(model.data(index) or "")
                col_width = max(col_width, font_metrics.horizontalAdvance(data) + 20)

            total_width += col_width

        # Determine if landscape is really needed based on content width
        page_width = 595  # Approximate A4 width in points
        if total_width > page_width * 0.9:  # Only use landscape if we really need it
            printer.setOrientation(QPrinter.Landscape)
        else:
            printer.setOrientation(QPrinter.Portrait)

        # Set up the painter
        painter = QPainter()
        if not painter.begin(printer):
            QMessageBox.critical(parent, "Export Error", "Could not open PDF file for writing.")
            return

        # Get actual page rect after orientation is set
        page_rect = printer.pageRect()
        page_width = page_rect.width()
        page_height = page_rect.height()

        # Calculate cell dimensions
        font_metrics = painter.fontMetrics()
        row_height = int(font_metrics.height() + 10)
        header_height = int(row_height * 1.5)

        # Calculate column widths based on content
        col_widths = []
        total_width = 0

        for column in range(columns):
            header_text = model.headerData(column, Qt.Horizontal) or f"Column {column + 1}"
            col_width = font_metrics.horizontalAdvance(header_text) + 20

            # Check data in all rows for this column
            for row in range(rows):
                index = model.index(row, column)
                data = str(model.data(index) or "")
                col_width = max(col_width, font_metrics.horizontalAdvance(data) + 20)

            # Ensure minimum width
            col_width = max(col_width, 80)

            col_widths.append(col_width)
            total_width += col_width

        # Scale column widths to fit page if needed
        margin = 40
        available_width = page_width - (2 * margin)

        if total_width > available_width:
            scale_factor = available_width / total_width
            col_widths = [int(w * scale_factor) for w in col_widths]
            total_width = sum(col_widths)

        # Set margins and table position
        x_start = int((page_width - total_width) / 2)  # Center the table
        y_start = margin

        # Draw title
        title_font = painter.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        painter.setFont(title_font)
        title_rect = QRect(margin, y_start, int(page_width - 2 * margin), int(row_height * 2))
        painter.drawText(title_rect, Qt.AlignCenter, title)

        # Reset font for table data
        normal_font = painter.font()
        normal_font.setPointSize(10)
        normal_font.setBold(False)
        painter.setFont(normal_font)

        # Move y position down for table start
        y_start += int(row_height * 3)

        # Draw table headers
        painter.setPen(Qt.black)
        x_pos = x_start

        # Draw header background
        header_bg_color = QColor(200, 200, 200)  # Light gray
        header_rect = QRect(x_start, y_start, total_width, header_height)
        painter.fillRect(header_rect, header_bg_color)

        # Draw header text and vertical lines
        for column in range(columns):
            header_text = model.headerData(column, Qt.Horizontal) or f"Column {column + 1}"
            cell_rect = QRect(int(x_pos), y_start, int(col_widths[column]), header_height)

            # Draw cell border
            painter.drawRect(cell_rect)

            # Draw header text
            text_rect = QRect(int(x_pos + 5), int(y_start + 5),
                              int(col_widths[column] - 10), int(header_height - 10))
            painter.drawText(text_rect, Qt.AlignCenter, header_text)

            x_pos += col_widths[column]

        # Draw horizontal line under headers
        painter.drawLine(x_start, int(y_start + header_height),
                         int(x_start + total_width), int(y_start + header_height))

        # Draw data rows
        y_pos = int(y_start + header_height)
        rows_per_page = int((page_height - y_pos - margin - 20) / row_height)  # Leave space for footer
        current_page = 1

        # Alternating row colors
        row_colors = [
            QColor(255, 255, 255),  # White
            QColor(240, 240, 240)  # Light gray
        ]

        for row in range(rows):
            # Check if we need a new page
            if row > 0 and row % rows_per_page == 0:
                # Add page number at bottom of current page
                footer_text = f"Page {current_page}"
                footer_rect = QRect(margin, int(page_height - margin),
                                    int(page_width - 2 * margin), margin)
                painter.drawText(footer_rect, Qt.AlignRight | Qt.AlignBottom, footer_text)

                printer.newPage()
                y_pos = margin
                current_page += 1

                # Redraw headers on new page
                x_pos = x_start
                header_rect = QRect(x_start, y_pos, total_width, header_height)
                painter.fillRect(header_rect, header_bg_color)

                for column in range(columns):
                    header_text = model.headerData(column, Qt.Horizontal) or f"Column {column + 1}"
                    cell_rect = QRect(int(x_pos), y_pos, int(col_widths[column]), header_height)
                    painter.drawRect(cell_rect)
                    text_rect = QRect(int(x_pos + 5), int(y_pos + 5),
                                      int(col_widths[column] - 10), int(header_height - 10))
                    painter.drawText(text_rect, Qt.AlignCenter, header_text)
                    x_pos += col_widths[column]

                y_pos += header_height

            x_pos = x_start

            # Set row background color (alternating)
            row_rect = QRect(x_start, y_pos, total_width, row_height)
            painter.fillRect(row_rect, row_colors[row % 2])

            # Draw cells in this row
            for column in range(columns):
                index = model.index(row, column)
                data = str(model.data(index) or "")

                cell_rect = QRect(int(x_pos), int(y_pos), int(col_widths[column]), int(row_height))

                # Draw cell border
                painter.drawRect(cell_rect)

                # Draw cell text
                text_rect = QRect(int(x_pos + 5), int(y_pos + 5),
                                  int(col_widths[column] - 10), int(row_height - 10))

                # Align numbers right, text left
                alignment = Qt.AlignRight if is_numeric(data) else Qt.AlignLeft
                alignment |= Qt.AlignVCenter

                painter.drawText(text_rect, alignment, data)

                x_pos += col_widths[column]

            y_pos += row_height

        # Draw final page number
        footer_text = f"Page {current_page}"
        if current_page > 1:
            footer_text += f" of {current_page}"

        footer_rect = QRect(margin, int(page_height - margin),
                            int(page_width - 2 * margin), margin)
        painter.drawText(footer_rect, Qt.AlignRight | Qt.AlignBottom, footer_text)

        painter.end()
        QMessageBox.information(parent, "Export Success", f"Data exported successfully to {file_path}")
    except Exception as e:
        QMessageBox.critical(parent, "Export Error", f"Failed to export to PDF: {str(e)}")

def is_numeric(text):
    """Check if a string represents a numeric value"""
    try:
        float(text)
        return True
    except (ValueError, TypeError):
        return False