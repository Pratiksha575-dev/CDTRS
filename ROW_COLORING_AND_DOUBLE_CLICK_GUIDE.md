# CDTRS Guide: Row Coloring & Double-Click Document Opening

This guide explains **only** the two specific features so you can easily apply them to your office codebase:
1. **Seamless Row Coloring** (with left urgency accent stripe & no vertical gridlines)
2. **Double-Click / Double-Tap Document Opening** across all tables

---

## Part 1: Row Coloring Logic

### 1. The Core Item Delegate (`RowColorItemDelegate`)
In Qt (`PySide6`), styling rows via stylesheets often causes individual cell gaps or gets overwritten. We use a single, lightweight `QStyledItemDelegate` that:
- Paints the background color smoothly across the entire row.
- Adds a solid 4px vertical urgency indicator on the first column.
- Removes ugly individual cell focus boxes.

Place this in a shared file (e.g. `frontend/components/priority_badge.py` or inside your table component):

```python
from datetime import date, datetime
from typing import Optional, Union, Dict, Any
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QBrush, QFont, QPainter
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QStyledItemDelegate, QStyleOptionViewItem, QStyle


class RowColorItemDelegate(QStyledItemDelegate):
    """Paints seamless row backgrounds with left-edge urgency stripes and no cell focus boxes."""
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        bg = index.data(Qt.BackgroundRole)
        fg = index.data(Qt.ForegroundRole)
        accent_color = index.data(Qt.UserRole + 1) # Urgency stripe color

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Paint row background
        if option.state & QStyle.State_Selected:
            if bg and isinstance(bg, (QBrush, QColor)):
                painter.fillRect(option.rect, bg)
            # Subtle selection overlay + border
            painter.fillRect(option.rect, QColor(37, 99, 235, 30))
            painter.setPen(QColor("#2563EB"))
            painter.drawLine(option.rect.topLeft(), option.rect.topRight())
            painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())
        else:
            if bg and isinstance(bg, (QBrush, QColor)):
                painter.fillRect(option.rect, bg)
            else:
                painter.fillRect(option.rect, QColor("#FFFFFF"))

            # Bottom separator line only (no vertical lines)
            painter.setPen(QColor("#F1F5F9"))
            painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())

        # 2. Left 4px vertical accent stripe on column 0
        if index.column() == 0 and accent_color:
            stripe_rect = QRect(option.rect.left(), option.rect.top(), 4, option.rect.height())
            painter.fillRect(stripe_rect, QColor(accent_color))

        painter.restore()

        # 3. Draw text without individual cell focus box
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.backgroundBrush = QBrush(Qt.NoBrush)
        opt.state &= ~QStyle.State_HasFocus # Strips cell focus rectangle
        if fg and isinstance(fg, (QBrush, QColor)):
            c = fg.color() if isinstance(fg, QBrush) else fg
            opt.palette.setColor(QPalette.Text, c)
            opt.palette.setColor(QPalette.HighlightedText, c)

        super().paint(painter, opt, index)
```

---

### 2. Urgency Color Calculation & Application Helper
Add these helper functions to calculate the deadline countdown and apply colors to a table row:

```python
def parse_deadline_date(deadline_val):
    if not deadline_val or str(deadline_val).strip() in ("-", "None", "", "null", "—"):
        return None
    if isinstance(deadline_val, datetime):
        return deadline_val.date()
    if isinstance(deadline_val, date):
        return deadline_val
    raw_str = str(deadline_val).strip().split()[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw_str, fmt).date()
        except ValueError:
            pass
    return None


def get_srs_priority_info(priority=None, deadline=None, status=None) -> Dict[str, Any]:
    today = date.today()
    dl_date = parse_deadline_date(deadline)
    prio_lower = str(priority or "Medium").strip().lower()
    status_lower = str(status or "").lower()
    days_left = (dl_date - today).days if dl_date else None

    # Closed / Completed
    if status_lower in ("closed", "completed"):
        return {
            "label": "Closed",
            "bg_color": "#DCFCE7", "text_color": "#166534", "accent_color": "#10B981",
            "deadline_str": dl_date.strftime("%Y-%m-%d") if dl_date else "-"
        }

    # Red: Overdue, Due Today, Urgent
    if (days_left is not None and days_left <= 0) or prio_lower in ("red", "urgent", "critical") or "overdue" in status_lower:
        lbl = f"Overdue ({abs(days_left)}d)" if (days_left is not None and days_left < 0) else ("Due Today" if days_left == 0 else "Urgent")
        return {
            "label": lbl,
            "bg_color": "#FFE4E6", "text_color": "#9F1239", "accent_color": "#E11D48",
            "deadline_str": f"{dl_date.strftime('%Y-%m-%d')} ({lbl})" if dl_date else "-"
        }

    # Orange: 1-3 days left or High
    if (days_left is not None and 1 <= days_left <= 3) or prio_lower in ("orange", "high"):
        note = f" ({days_left}d left)" if (days_left is not None and 1 <= days_left <= 3) else ""
        return {
            "label": f"High{note}",
            "bg_color": "#FFEDD5", "text_color": "#9A3412", "accent_color": "#EA580C",
            "deadline_str": f"{dl_date.strftime('%Y-%m-%d')}{note}" if dl_date else "-"
        }

    # Yellow: 4-7 days left or Medium
    if (days_left is not None and 4 <= days_left <= 7) or prio_lower in ("yellow", "medium"):
        note = f" ({days_left}d left)" if (days_left is not None and 4 <= days_left <= 7) else ""
        return {
            "label": f"Medium{note}",
            "bg_color": "#FEF9C3", "text_color": "#854D0E", "accent_color": "#EAB308",
            "deadline_str": f"{dl_date.strftime('%Y-%m-%d')}{note}" if dl_date else "-"
        }

    # Green: >7 days left or Normal
    note = f" ({days_left}d left)" if (days_left is not None and days_left > 7) else ""
    return {
        "label": f"Normal{note}",
        "bg_color": "#DCFCE7", "text_color": "#166534", "accent_color": "#10B981",
        "deadline_str": f"{dl_date.strftime('%Y-%m-%d')}{note}" if dl_date else "-"
    }


def apply_srs_row_styling(table: QTableWidget, row: int, priority_col: Optional[int], deadline_col: Optional[int], priority, deadline, status=None):
    """Call this inside your table loop for each row."""
    table.setShowGrid(False) # Hides vertical grid lines
    if not isinstance(table.itemDelegate(), RowColorItemDelegate):
        table.setItemDelegate(RowColorItemDelegate(table))

    info = get_srs_priority_info(priority=priority, deadline=deadline, status=status)
    bg_brush = QBrush(QColor(info["bg_color"]))
    text_brush = QBrush(QColor(info["text_color"]))
    accent = info["accent_color"]

    bold_font = QFont("Segoe UI", 9)
    bold_font.setBold(True)
    reg_font = QFont("Segoe UI", 9)

    # Priority cell
    if priority_col is not None and 0 <= priority_col < table.columnCount():
        p_item = QTableWidgetItem(info["label"])
        p_item.setTextAlignment(Qt.AlignCenter)
        p_item.setFont(bold_font)
        p_item.setBackground(bg_brush)
        p_item.setForeground(text_brush)
        p_item.setData(Qt.UserRole + 1, accent)
        table.setItem(row, priority_col, p_item)

    # Deadline cell
    if deadline_col is not None and 0 <= deadline_col < table.columnCount():
        d_item = QTableWidgetItem(info["deadline_str"])
        d_item.setTextAlignment(Qt.AlignCenter)
        d_item.setFont(bold_font)
        d_item.setBackground(bg_brush)
        d_item.setForeground(text_brush)
        d_item.setData(Qt.UserRole + 1, accent)
        table.setItem(row, deadline_col, d_item)

    # Apply background color and accent data to all other cells in the row
    for c in range(table.columnCount()):
        item = table.item(row, c)
        if not item:
            item = QTableWidgetItem("-")
            table.setItem(row, c, item)
        item.setBackground(bg_brush)
        item.setForeground(text_brush)
        item.setData(Qt.UserRole + 1, accent)
        if c == 0:
            item.setFont(bold_font)
        elif c not in (priority_col, deadline_col):
            item.setFont(reg_font)
```

---

### 3. Usage in Any Table Loop
Whenever you populate a table (`for row, doc in enumerate(documents):`), just call `apply_srs_row_styling`:

```python
# Example:
apply_srs_row_styling(
    table=self.table,
    row=row,
    priority_col=2,      # Index of Priority column (or None if not present)
    deadline_col=5,      # Index of Deadline column (or None if not present)
    priority=doc.priority,
    deadline=doc.deadline,
    status=doc.status
)
```

---

## Part 2: Double-Click / Double-Tap Document Opening

To make double-clicking any row open the document, connect `self.table.doubleClicked` right after creating the `QTableWidget`.

### 1. In `DocumentsPage` / `PriorityPage`:
```python
self.table.doubleClicked.connect(self.view_document)

def view_document(self):
    selected_doc = self.table.get_selected_document()
    if selected_doc:
        dialog = DocumentViewerDialog(selected_doc, parent=self)
        dialog.exec()
```

### 2. In `DirectorInboxPage`:
```python
self.table.doubleClicked.connect(self.review_document)

def review_document(self):
    row = self.table.currentRow()
    if 0 <= row < len(self._displayed_docs):
        doc = self._displayed_docs[row]
        # Open Director Review Dialog
        dialog = DirectorReviewDialog(doc, parent=self)
        if dialog.exec():
            self.refresh()
```

### 3. In `HODInboxPage`:
```python
self.table.doubleClicked.connect(self.open_document)

def open_document(self):
    row = self.table.currentRow()
    if 0 <= row < len(self._displayed_docs):
        doc = self._displayed_docs[row]
        # Open HOD Assignment / Guidance Dialog
        dialog = HODAssignEmployeeDialog(doc, parent=self)
        if dialog.exec():
            self.load_inbox()
```

### 4. In `EmployeeTasksPage`:
```python
self.table.doubleClicked.connect(self.open_task)

def open_task(self):
    row = self.table.currentRow()
    if 0 <= row < len(self._displayed_tasks):
        task = self._displayed_tasks[row]
        # Open Progress Submission Dialog
        dialog = SubmitProgressDialog(task, parent=self)
        if dialog.exec():
            self.load_tasks()
```

### 5. In `DashboardPage`:
```python
self.table.doubleClicked.connect(self._handle_view_selected)

def _handle_view_selected(self):
    row = self.table.currentRow()
    if 0 <= row < len(self._displayed_docs):
        selected_doc = self._displayed_docs[row]
        self.view_requested.emit(selected_doc, self.role)
```
