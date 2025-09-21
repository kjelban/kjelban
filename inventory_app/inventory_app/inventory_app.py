# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- Database Setup ---
DB_NAME = 'college_inventory.db'

def setup_database():
    """Creates the database and tables if they don't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Suppliers Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        contact_info TEXT
    )
    ''')

    # Employees Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        position TEXT
    )
    ''')
    
    # Categories Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    ''')

    # Units Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    ''')

    # Items Table
    # Now uses foreign keys for category and unit
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        quantity INTEGER NOT NULL DEFAULT 0,
        category_id INTEGER,
        unit_id INTEGER,
        FOREIGN KEY (category_id) REFERENCES categories(id),
        FOREIGN KEY (unit_id) REFERENCES units(id)
    )
    ''')
    
    # Transactions Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        transaction_type TEXT NOT NULL, -- 'RECEIVE' or 'ISSUE'
        transaction_date TEXT NOT NULL,
        employee_id INTEGER NOT NULL,
        supplier_id INTEGER, -- Only for RECEIVE transactions
        notes TEXT,
        FOREIGN KEY (item_id) REFERENCES items(id),
        FOREIGN KEY (employee_id) REFERENCES employees(id),
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
    )
    ''')
    
    conn.commit()
    conn.close()

# --- Main Application Class ---
class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("نظام إدارة مخزن كلية العلوم والتقنية")
        self.geometry("1200x800")
        self.style = ttk.Style(self)
        self.style.theme_use('clam')

        # Create a notebook (tabbed interface)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Create frames for each tab
        self.dashboard_frame = ttk.Frame(self.notebook)
        self.items_main_frame = ttk.Frame(self.notebook) # Main frame for items sub-tabs
        self.suppliers_frame = ttk.Frame(self.notebook)
        self.employees_frame = ttk.Frame(self.notebook)
        self.transactions_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.dashboard_frame, text="لوحة التحكم")
        self.notebook.add(self.items_main_frame, text="المواد")
        self.notebook.add(self.suppliers_frame, text="الموردين")
        self.notebook.add(self.employees_frame, text="الموظفون")
        self.notebook.add(self.transactions_frame, text="الحركات")

        # Create sub-notebook for items
        self.items_notebook = ttk.Notebook(self.items_main_frame)
        self.items_notebook.pack(fill='both', expand=True)

        # Create frames for items sub-tabs
        self.items_frame = ttk.Frame(self.items_notebook)
        self.categories_frame = ttk.Frame(self.items_notebook)
        self.units_frame = ttk.Frame(self.items_notebook)

        self.items_notebook.add(self.items_frame, text="إدارة الأصناف")
        self.items_notebook.add(self.categories_frame, text="إدارة الفئات")
        self.items_notebook.add(self.units_frame, text="إدارة الوحدات")

        # Initialize each tab
        self.create_dashboard_tab()
        self.create_items_tab()
        self.create_categories_tab()
        self.create_units_tab()
        self.create_suppliers_tab()
        self.create_employees_tab()
        self.create_transactions_tab()

        # Make the dashboard the default tab
        self.notebook.select(self.dashboard_frame)

    def get_connection(self):
        return sqlite3.connect(DB_NAME)

    # --- Dashboard Tab ---
    def create_dashboard_tab(self):
        main_container = ttk.Frame(self.dashboard_frame, padding="10")
        main_container.pack(fill='both', expand=True)

        cards_frame = ttk.Frame(main_container)
        cards_frame.pack(fill='x', pady=(0, 20))

        self.style.configure('Card.TFrame', background='#f0f0f0', relief='raised', borderwidth=1)
        self.style.configure('CardTitle.TLabel', font=('Helvetica', 12, 'bold'), background='#f0f0f0')
        self.style.configure('CardValue.TLabel', font=('Helvetica', 24, 'bold'), background='#f0f0f0')

        self.create_card(cards_frame, "إجمالي الأصناف", self.get_total_items, 0)
        self.create_card(cards_frame, "الأصناف منخفضة المخزون", self.get_low_stock_items, 1)
        self.create_card(cards_frame, "المستلم اليوم", self.get_today_transactions, 2, transaction_type='RECEIVE')
        self.create_card(cards_frame, "المسلم اليوم", self.get_today_transactions, 3, transaction_type='ISSUE')

        middle_frame = ttk.Frame(main_container)
        middle_frame.pack(fill='both', expand=True)

        chart_container = ttk.LabelFrame(middle_frame, text="نظرة عامة على المخزون", padding="10")
        chart_container.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        self.chart_figure, self.chart_ax = plt.subplots(figsize=(6, 4), dpi=80)
        self.chart_canvas = FigureCanvasTkAgg(self.chart_figure, master=chart_container)
        self.chart_canvas.get_tk_widget().pack(fill='both', expand=True)
        self.update_overview_chart()

        activity_container = ttk.LabelFrame(middle_frame, text="الأنشطة الحديثة", padding="10")
        activity_container.pack(side='right', fill='both', expand=True)

        self.activity_tree = ttk.Treeview(activity_container, columns=('Date', 'Type', 'Item', 'Qty', 'Employee'), show='headings', height=10)
        self.activity_tree.heading('Date', text='التاريخ')
        self.activity_tree.heading('Type', text='النوع')
        self.activity_tree.heading('Item', text='المادة')
        self.activity_tree.heading('Qty', text='الكمية')
        self.activity_tree.heading('Employee', text='الموظف')
        
        self.activity_tree.column('Date', width=120)
        self.activity_tree.column('Type', width=80, anchor='center')
        self.activity_tree.column('Qty', width=60, anchor='center')
        
        self.activity_tree.pack(fill='both', expand=True)
        self.update_recent_activity()

    def create_card(self, parent, title, command_func, column, **kwargs):
        card = ttk.Frame(parent, style='Card.TFrame', padding="15")
        card.grid(row=0, column=column, padx=10, pady=10, sticky="nsew")
        parent.grid_columnconfigure(column, weight=1)

        title_label = ttk.Label(card, text=title, style='CardTitle.TLabel')
        title_label.pack()
        
        value = command_func(**kwargs)
        value_label = ttk.Label(card, text=str(value), style='CardValue.TLabel')
        value_label.pack()

    def get_total_items(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM items")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_low_stock_items(self, threshold=10):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM items WHERE quantity < ?", (threshold,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_today_transactions(self, transaction_type=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        today_date = datetime.now().strftime('%Y-%m-%d')
        if transaction_type:
            cursor.execute("SELECT COUNT(*) FROM transactions WHERE transaction_type = ? AND DATE(transaction_date) = ?", (transaction_type, today_date))
        else:
            cursor.execute("SELECT COUNT(*) FROM transactions WHERE DATE(transaction_date) = ?", (today_date,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def update_overview_chart(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT c.name, COUNT(i.id) FROM categories c LEFT JOIN items i ON c.id = i.category_id GROUP BY c.name")
        categories_data = cursor.fetchall()
        conn.close()

        if not categories_data or all(count == 0 for _, count in categories_data):
            self.chart_ax.clear()
            self.chart_ax.text(0.5, 0.5, 'لا توجد بيانات لعرضها', horizontalalignment='center', verticalalignment='center', transform=self.chart_ax.transAxes)
        else:
            labels = []
            low_stock_counts = []
            ok_stock_counts = []
            
            threshold = 10
            for category, total in categories_data:
                if total > 0:
                    conn = self.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM items i JOIN categories c ON i.category_id = c.id WHERE c.name = ? AND i.quantity < ?", (category, threshold))
                    low = cursor.fetchone()[0]
                    conn.close()
                    ok = total - low
                    
                    labels.append(f"{category} (منخفض: {low})")
                    low_stock_counts.append(low)
                    ok_stock_counts.append(ok)

            self.chart_ax.clear()
            sizes = ok_stock_counts
            explode = [0.05] * len(labels)
            
            self.chart_ax.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%', shadow=True, startangle=90)
            self.chart_ax.axis('equal')
            self.chart_ax.set_title('نسبة الأصناف ذات المخزون الكافي حسب الفئة')

        self.chart_canvas.draw()

    def update_recent_activity(self):
        for i in self.activity_tree.get_children():
            self.activity_tree.delete(i)
            
        conn = self.get_connection()
        cursor = conn.cursor()
        query = '''
        SELECT 
            t.transaction_date, t.transaction_type, 
            i.name AS item_name, t.quantity,
            e.name AS employee_name
        FROM transactions t
        JOIN items i ON t.item_id = i.id
        JOIN employees e ON t.employee_id = e.id
        ORDER BY t.transaction_date DESC
        LIMIT 20
        '''
        cursor.execute(query)
        for row in cursor.fetchall():
            formatted_date = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
            type_ar = "استلام" if row[1] == 'RECEIVE' else "تسليم"
            self.activity_tree.insert('', 'end', values=(formatted_date, type_ar, row[2], row[3], row[4]))
        conn.close()

    # --- Units Tab ---
    def create_units_tab(self):
        form_frame = ttk.LabelFrame(self.units_frame, text="إضافة/تعديل وحدة")
        form_frame.pack(padx=10, pady=10, fill='x')

        ttk.Label(form_frame, text="اسم الوحدة:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.unit_name_entry = ttk.Entry(form_frame, width=40)
        self.unit_name_entry.grid(row=0, column=1, padx=5, pady=5)
        
        self.unit_id_var = tk.StringVar()

        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="إضافة وحدة", command=self.add_unit).pack(side='left', padx=5)
        ttk.Button(button_frame, text="تعديل وحدة", command=self.update_unit).pack(side='left', padx=5)
        ttk.Button(button_frame, text="مسح الحقول", command=self.clear_unit_form).pack(side='left', padx=5)

        tree_frame = ttk.LabelFrame(self.units_frame, text="قائمة الوحدات")
        tree_frame.pack(padx=10, pady=10, fill='both', expand=True)

        self.units_tree = ttk.Treeview(tree_frame, columns=('ID', 'Name'), show='headings')
        self.units_tree.heading('ID', text='الرقم')
        self.units_tree.heading('Name', text='اسم الوحدة')
        self.units_tree.column('ID', width=50, anchor='center')
        self.units_tree.pack(fill='both', expand=True)
        self.units_tree.bind('<Double-1>', self.load_unit_data)

        ttk.Button(tree_frame, text="حذف المحدد", command=self.delete_unit).pack(pady=5)
        
        self.refresh_units_tree()

    def clear_unit_form(self):
        self.unit_name_entry.delete(0, tk.END)
        self.unit_id_var.set("")

    def add_unit(self):
        name = self.unit_name_entry.get()
        if not name:
            messagebox.showerror("خطأ", "اسم الوحدة مطلوب.")
            return
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO units (name) VALUES (?)", (name,))
            conn.commit()
            messagebox.showinfo("نجاح", "تمت إضافة الوحدة بنجاح.")
            self.clear_unit_form()
            self.refresh_units_tree()
        except sqlite3.IntegrityError:
            messagebox.showerror("خطأ", "هذه الوحدة موجودة بالفعل.")
        finally:
            conn.close()

    def load_unit_data(self, event):
        selected_item = self.units_tree.focus()
        if not selected_item: return
        item_data = self.units_tree.item(selected_item)
        values = item_data['values']
        self.unit_id_var.set(values[0])
        self.unit_name_entry.delete(0, tk.END)
        self.unit_name_entry.insert(0, values[1])

    def update_unit(self):
        unit_id = self.unit_id_var.get()
        if not unit_id:
            messagebox.showerror("خطأ", "الرجاء اختيار وحدة للتعديل.")
            return
        name = self.unit_name_entry.get()
        if not name:
            messagebox.showerror("خطأ", "اسم الوحدة مطلوب.")
            return
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE units SET name=? WHERE id=?", (name, unit_id))
            conn.commit()
            messagebox.showinfo("نجاح", "تم تعديل الوحدة بنجاح.")
            self.clear_unit_form()
            self.refresh_units_tree()
        except sqlite3.IntegrityError:
            messagebox.showerror("خطأ", "هذه الوحدة موجودة بالفعل.")
        finally:
            conn.close()

    def delete_unit(self):
        selected_item = self.units_tree.focus()
        if not selected_item:
            messagebox.showerror("خطأ", "الرجاء اختيار وحدة للحذف.")
            return
        unit_id = self.units_tree.item(selected_item)['values'][0]
        if messagebox.askyesno("تأكيد الحذف", "هل أنت متأكد من حذف هذه الوحدة؟ لا يمكن حذف وحدة مرتبطة بصنف."):
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM units WHERE id=?", (unit_id,))
                conn.commit()
                messagebox.showinfo("نجاح", "تم حذف الوحدة بنجاح.")
                self.refresh_units_tree()
            except sqlite3.IntegrityError:
                 messagebox.showerror("خطأ", "لا يمكن حذف هذه الوحدة لأنها مرتبطة بأحد الأصناف.")
            finally:
                conn.close()

    def refresh_units_tree(self):
        for i in self.units_tree.get_children():
            self.units_tree.delete(i)
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM units ORDER BY name")
        for row in cursor.fetchall():
            self.units_tree.insert('', 'end', values=row)
        conn.close()
        # Update comboboxes in other tabs
        if hasattr(self, 'item_unit_combobox'):
            self.refresh_item_comboboxes()


    # --- Categories Tab ---
    def create_categories_tab(self):
        form_frame = ttk.LabelFrame(self.categories_frame, text="إضافة/تعديل فئة")
        form_frame.pack(padx=10, pady=10, fill='x')

        ttk.Label(form_frame, text="اسم الفئة:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.category_name_entry = ttk.Entry(form_frame, width=40)
        self.category_name_entry.grid(row=0, column=1, padx=5, pady=5)
        
        self.category_id_var = tk.StringVar()

        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="إضافة فئة", command=self.add_category).pack(side='left', padx=5)
        ttk.Button(button_frame, text="تعديل فئة", command=self.update_category).pack(side='left', padx=5)
        ttk.Button(button_frame, text="مسح الحقول", command=self.clear_category_form).pack(side='left', padx=5)

        tree_frame = ttk.LabelFrame(self.categories_frame, text="قائمة الفئات")
        tree_frame.pack(padx=10, pady=10, fill='both', expand=True)

        self.categories_tree = ttk.Treeview(tree_frame, columns=('ID', 'Name'), show='headings')
        self.categories_tree.heading('ID', text='الرقم')
        self.categories_tree.heading('Name', text='اسم الفئة')
        self.categories_tree.column('ID', width=50, anchor='center')
        self.categories_tree.pack(fill='both', expand=True)
        self.categories_tree.bind('<Double-1>', self.load_category_data)

        ttk.Button(tree_frame, text="حذف المحدد", command=self.delete_category).pack(pady=5)
        
        self.refresh_categories_tree()

    def clear_category_form(self):
        self.category_name_entry.delete(0, tk.END)
        self.category_id_var.set("")

    def add_category(self):
        name = self.category_name_entry.get()
        if not name:
            messagebox.showerror("خطأ", "اسم الفئة مطلوب.")
            return
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO categories (name) VALUES (?)", (name,))
            conn.commit()
            messagebox.showinfo("نجاح", "تمت إضافة الفئة بنجاح.")
            self.clear_category_form()
            self.refresh_categories_tree()
        except sqlite3.IntegrityError:
            messagebox.showerror("خطأ", "هذه الفئة موجودة بالفعل.")
        finally:
            conn.close()

    def load_category_data(self, event):
        selected_item = self.categories_tree.focus()
        if not selected_item: return
        item_data = self.categories_tree.item(selected_item)
        values = item_data['values']
        self.category_id_var.set(values[0])
        self.category_name_entry.delete(0, tk.END)
        self.category_name_entry.insert(0, values[1])

    def update_category(self):
        category_id = self.category_id_var.get()
        if not category_id:
            messagebox.showerror("خطأ", "الرجاء اختيار فئة للتعديل.")
            return
        name = self.category_name_entry.get()
        if not name:
            messagebox.showerror("خطأ", "اسم الفئة مطلوب.")
            return
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE categories SET name=? WHERE id=?", (name, category_id))
            conn.commit()
            messagebox.showinfo("نجاح", "تم تعديل الفئة بنجاح.")
            self.clear_category_form()
            self.refresh_categories_tree()
        except sqlite3.IntegrityError:
            messagebox.showerror("خطأ", "هذه الفئة موجودة بالفعل.")
        finally:
            conn.close()

    def delete_category(self):
        selected_item = self.categories_tree.focus()
        if not selected_item:
            messagebox.showerror("خطأ", "الرجاء اختيار فئة للحذف.")
            return
        category_id = self.categories_tree.item(selected_item)['values'][0]
        if messagebox.askyesno("تأكيد الحذف", "هل أنت متأكد من حذف هذه الفئة؟ لا يمكن حذف فئة مرتبطة بصنف."):
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM categories WHERE id=?", (category_id,))
                conn.commit()
                messagebox.showinfo("نجاح", "تم حذف الفئة بنجاح.")
                self.refresh_categories_tree()
            except sqlite3.IntegrityError:
                 messagebox.showerror("خطأ", "لا يمكن حذف هذه الفئة لأنها مرتبطة بأحد الأصناف.")
            finally:
                conn.close()

    def refresh_categories_tree(self):
        for i in self.categories_tree.get_children():
            self.categories_tree.delete(i)
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM categories ORDER BY name")
        for row in cursor.fetchall():
            self.categories_tree.insert('', 'end', values=row)
        conn.close()
        # Update comboboxes and chart in other tabs
        if hasattr(self, 'item_category_combobox'):
            self.refresh_item_comboboxes()
        if hasattr(self, 'chart_ax'):
            self.update_overview_chart()


    # --- Items Tab ---
    def create_items_tab(self):
        form_frame = ttk.LabelFrame(self.items_frame, text="إضافة/تعديل صنف")
        form_frame.pack(padx=10, pady=10, fill='x')

        ttk.Label(form_frame, text="اسم الصنف:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.item_name_entry = ttk.Entry(form_frame, width=40)
        self.item_name_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="الوصف:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.item_desc_entry = ttk.Entry(form_frame, width=40)
        self.item_desc_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="الكمية:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.item_qty_entry = ttk.Entry(form_frame, width=40)
        self.item_qty_entry.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="الفئة:").grid(row=3, column=0, padx=5, pady=5, sticky='w')
        self.item_category_combobox = ttk.Combobox(form_frame, state="readonly", width=38)
        self.item_category_combobox.grid(row=3, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="الوحدة:").grid(row=4, column=0, padx=5, pady=5, sticky='w')
        self.item_unit_combobox = ttk.Combobox(form_frame, state="readonly", width=38)
        self.item_unit_combobox.grid(row=4, column=1, padx=5, pady=5)
        
        self.item_id_var = tk.StringVar()

        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="إضافة صنف", command=self.add_item).pack(side='left', padx=5)
        ttk.Button(button_frame, text="تعديل صنف", command=self.update_item).pack(side='left', padx=5)
        ttk.Button(button_frame, text="مسح الحقول", command=self.clear_item_form).pack(side='left', padx=5)

        tree_frame = ttk.LabelFrame(self.items_frame, text="قائمة الأصناف")
        tree_frame.pack(padx=10, pady=10, fill='both', expand=True)

        self.items_tree = ttk.Treeview(tree_frame, columns=('ID', 'Name', 'Description', 'Quantity', 'Category', 'Unit'), show='headings')
        self.items_tree.heading('ID', text='الرقم')
        self.items_tree.heading('Name', text='اسم الصنف')
        self.items_tree.heading('Description', text='الوصف')
        self.items_tree.heading('Quantity', text='الكمية')
        self.items_tree.heading('Category', text='الفئة')
        self.items_tree.heading('Unit', text='الوحدة')

        self.items_tree.column('ID', width=40, anchor='center')
        self.items_tree.column('Quantity', width=80, anchor='center')
        
        self.items_tree.pack(fill='both', expand=True)
        self.items_tree.bind('<Double-1>', self.load_item_data)

        ttk.Button(tree_frame, text="حذف المحدد", command=self.delete_item).pack(pady=5)
        
        self.refresh_item_comboboxes()
        self.refresh_items_tree()

    def clear_item_form(self):
        self.item_name_entry.delete(0, tk.END)
        self.item_desc_entry.delete(0, tk.END)
        self.item_qty_entry.delete(0, tk.END)
        self.item_category_combobox.set('')
        self.item_unit_combobox.set('')
        self.item_id_var.set("")

    def refresh_item_comboboxes(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        # Refresh Categories
        cursor.execute("SELECT name FROM categories ORDER BY name")
        categories = [row[0] for row in cursor.fetchall()]
        self.item_category_combobox['values'] = categories
        # Refresh Units
        cursor.execute("SELECT name FROM units ORDER BY name")
        units = [row[0] for row in cursor.fetchall()]
        self.item_unit_combobox['values'] = units
        conn.close()
        # Also refresh transaction combobox
        if hasattr(self, 'trans_item_combobox'):
            self.refresh_comboboxes()


    def add_item(self):
        name = self.item_name_entry.get()
        desc = self.item_desc_entry.get()
        qty_str = self.item_qty_entry.get()
        category_name = self.item_category_combobox.get()
        unit_name = self.item_unit_combobox.get()

        if not all([name, qty_str, category_name, unit_name]):
            messagebox.showerror("خطأ", "جميع الحقول مطلوبة ما عدا الوصف.")
            return

        try:
            qty = int(qty_str)
        except ValueError:
            messagebox.showerror("خطأ", "الكمية يجب أن تكون رقماً.")
            return

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM categories WHERE name=?", (category_name,))
            category_id = cursor.fetchone()[0]
            cursor.execute("SELECT id FROM units WHERE name=?", (unit_name,))
            unit_id = cursor.fetchone()[0]

            cursor.execute("INSERT INTO items (name, description, quantity, category_id, unit_id) VALUES (?, ?, ?, ?, ?)", 
                           (name, desc, qty, category_id, unit_id))
            conn.commit()
            messagebox.showinfo("نجاح", "تمت إضافة الصنف بنجاح.")
            self.clear_item_form()
            self.refresh_items_tree()
        except sqlite3.IntegrityError:
            messagebox.showerror("خطأ", "هذا الصنف موجود بالفعل.")
        finally:
            conn.close()

    def load_item_data(self, event):
        selected_item = self.items_tree.focus()
        if not selected_item: return
        
        item_data = self.items_tree.item(selected_item)
        values = item_data['values']
        
        self.item_id_var.set(values[0])
        self.item_name_entry.delete(0, tk.END)
        self.item_name_entry.insert(0, values[1])
        self.item_desc_entry.delete(0, tk.END)
        self.item_desc_entry.insert(0, values[2])
        self.item_qty_entry.delete(0, tk.END)
        self.item_qty_entry.insert(0, values[3])
        self.item_category_combobox.set(values[4])
        self.item_unit_combobox.set(values[5])

    def update_item(self):
        item_id = self.item_id_var.get()
        if not item_id:
            messagebox.showerror("خطأ", "الرجاء اختيار صنف للتعديل.")
            return

        name = self.item_name_entry.get()
        desc = self.item_desc_entry.get()
        qty_str = self.item_qty_entry.get()
        category_name = self.item_category_combobox.get()
        unit_name = self.item_unit_combobox.get()

        if not all([name, qty_str, category_name, unit_name]):
            messagebox.showerror("خطأ", "جميع الحقول مطلوبة ما عدا الوصف.")
            return
        try:
            qty = int(qty_str)
        except ValueError:
            messagebox.showerror("خطأ", "الكمية يجب أن تكون رقماً.")
            return

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM categories WHERE name=?", (category_name,))
            category_id = cursor.fetchone()[0]
            cursor.execute("SELECT id FROM units WHERE name=?", (unit_name,))
            unit_id = cursor.fetchone()[0]

            cursor.execute("UPDATE items SET name=?, description=?, quantity=?, category_id=?, unit_id=? WHERE id=?", 
                           (name, desc, qty, category_id, unit_id, item_id))
            conn.commit()
            messagebox.showinfo("نجاح", "تم تعديل الصنف بنجاح.")
            self.clear_item_form()
            self.refresh_items_tree()
        except sqlite3.IntegrityError:
            messagebox.showerror("خطأ", "هذا الصنف موجود بالفعل.")
        finally:
            conn.close()

    def delete_item(self):
        selected_item = self.items_tree.focus()
        if not selected_item:
            messagebox.showerror("خطأ", "الرجاء اختيار صنف للحذف.")
            return
        
        item_id = self.items_tree.item(selected_item)['values'][0]
        
        if messagebox.askyesno("تأكيد الحذف", "هل أنت متأكد من حذف هذا الصنف؟ سيتم حذف جميع سجلاته المتعلقة بالحركات."):
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE item_id=?", (item_id,))
            cursor.execute("DELETE FROM items WHERE id=?", (item_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("نجاح", "تم حذف الصنف بنجاح.")
            self.refresh_items_tree()

    def refresh_items_tree(self):
        for i in self.items_tree.get_children():
            self.items_tree.delete(i)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        query = '''
        SELECT 
            i.id, i.name, i.description, i.quantity, 
            c.name AS category_name, u.name AS unit_name
        FROM items i
        LEFT JOIN categories c ON i.category_id = c.id
        LEFT JOIN units u ON i.unit_id = u.id
        ORDER BY i.name
        '''
        cursor.execute(query)
        for row in cursor.fetchall():
            self.items_tree.insert('', 'end', values=row)
        conn.close()
        # Update dashboard when items change
        if hasattr(self, 'chart_ax'):
            self.update_overview_chart()
        if hasattr(self, 'trans_item_combobox'):
            self.refresh_comboboxes()


    # --- Suppliers Tab ---
    def create_suppliers_tab(self):
        form_frame = ttk.LabelFrame(self.suppliers_frame, text="إضافة مورد")
        form_frame.pack(padx=10, pady=10, fill='x')

        ttk.Label(form_frame, text="اسم المورد:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.supplier_name_entry = ttk.Entry(form_frame, width=40)
        self.supplier_name_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="معلومات الاتصال:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.supplier_contact_entry = ttk.Entry(form_frame, width=40)
        self.supplier_contact_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(form_frame, text="إضافة مورد", command=self.add_supplier).grid(row=2, column=0, columnspan=2, pady=10)

        tree_frame = ttk.LabelFrame(self.suppliers_frame, text="قائمة الموردين")
        tree_frame.pack(padx=10, pady=10, fill='both', expand=True)

        self.suppliers_tree = ttk.Treeview(tree_frame, columns=('ID', 'Name', 'Contact'), show='headings')
        self.suppliers_tree.heading('ID', text='الرقم')
        self.suppliers_tree.heading('Name', text='اسم المورد')
        self.suppliers_tree.heading('Contact', text='معلومات الاتصال')
        self.suppliers_tree.column('ID', width=50, anchor='center')
        self.suppliers_tree.pack(fill='both', expand=True)
        
        self.refresh_suppliers_tree()

    def add_supplier(self):
        name = self.supplier_name_entry.get()
        contact = self.supplier_contact_entry.get()
        if not name:
            messagebox.showerror("خطأ", "اسم المورد مطلوب.")
            return

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO suppliers (name, contact_info) VALUES (?, ?)", (name, contact))
            conn.commit()
            messagebox.showinfo("نجاح", "تمت إضافة المورد بنجاح.")
            self.supplier_name_entry.delete(0, tk.END)
            self.supplier_contact_entry.delete(0, tk.END)
            self.refresh_suppliers_tree()
        except sqlite3.IntegrityError:
            messagebox.showerror("خطأ", "هذا المورد موجود بالفعل.")
        finally:
            conn.close()

    def refresh_suppliers_tree(self):
        for i in self.suppliers_tree.get_children():
            self.suppliers_tree.delete(i)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, contact_info FROM suppliers ORDER BY name")
        for row in cursor.fetchall():
            self.suppliers_tree.insert('', 'end', values=row)
        conn.close()
        if hasattr(self, 'trans_supplier_combobox'):
            self.refresh_comboboxes()


    # --- Employees Tab ---
    def create_employees_tab(self):
        form_frame = ttk.LabelFrame(self.employees_frame, text="إضافة موظف")
        form_frame.pack(padx=10, pady=10, fill='x')

        ttk.Label(form_frame, text="اسم الموظف:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.employee_name_entry = ttk.Entry(form_frame, width=40)
        self.employee_name_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="المنصب:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.employee_position_entry = ttk.Entry(form_frame, width=40)
        self.employee_position_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(form_frame, text="إضافة موظف", command=self.add_employee).grid(row=2, column=0, columnspan=2, pady=10)

        tree_frame = ttk.LabelFrame(self.employees_frame, text="قائمة الموظفين")
        tree_frame.pack(padx=10, pady=10, fill='both', expand=True)

        self.employees_tree = ttk.Treeview(tree_frame, columns=('ID', 'Name', 'Position'), show='headings')
        self.employees_tree.heading('ID', text='الرقم')
        self.employees_tree.heading('Name', text='اسم الموظف')
        self.employees_tree.heading('Position', text='المنصب')
        self.employees_tree.column('ID', width=50, anchor='center')
        self.employees_tree.pack(fill='both', expand=True)

        self.refresh_employees_tree()

    def add_employee(self):
        name = self.employee_name_entry.get()
        position = self.employee_position_entry.get()
        if not name:
            messagebox.showerror("خطأ", "اسم الموظف مطلوب.")
            return

        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO employees (name, position) VALUES (?, ?)", (name, position))
            conn.commit()
            messagebox.showinfo("نجاح", "تمت إضافة الموظف بنجاح.")
            self.employee_name_entry.delete(0, tk.END)
            self.employee_position_entry.delete(0, tk.END)
            self.refresh_employees_tree()
        except sqlite3.IntegrityError:
            messagebox.showerror("خطأ", "هذا الموظف موجود بالفعل.")
        finally:
            conn.close()

    def refresh_employees_tree(self):
        for i in self.employees_tree.get_children():
            self.employees_tree.delete(i)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, position FROM employees ORDER BY name")
        for row in cursor.fetchall():
            self.employees_tree.insert('', 'end', values=row)
        conn.close()
        if hasattr(self, 'trans_employee_combobox'):
            self.refresh_comboboxes()


    # --- Transactions Tab ---
    def create_transactions_tab(self):
        type_frame = ttk.Frame(self.transactions_frame)
        type_frame.pack(pady=10)
        
        ttk.Label(type_frame, text="نوع الحركة:", font=('Helvetica', 12, 'bold')).pack(side='left', padx=10)
        self.transaction_type_var = tk.StringVar(value="RECEIVE")
        ttk.Radiobutton(type_frame, text="استلام مواد", variable=self.transaction_type_var, value="RECEIVE", command=self.toggle_supplier_field).pack(side='left', padx=10)
        ttk.Radiobutton(type_frame, text="تسليم مواد", variable=self.transaction_type_var, value="ISSUE", command=self.toggle_supplier_field).pack(side='left', padx=10)

        form_frame = ttk.LabelFrame(self.transactions_frame, text="تسجيل حركة جديدة")
        form_frame.pack(padx=10, pady=10, fill='x')

        ttk.Label(form_frame, text="المادة:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.trans_item_combobox = ttk.Combobox(form_frame, state="readonly", width=37)
        self.trans_item_combobox.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(form_frame, text="الكمية:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.trans_qty_entry = ttk.Entry(form_frame, width=40)
        self.trans_qty_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="الموظف:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.trans_employee_combobox = ttk.Combobox(form_frame, state="readonly", width=37)
        self.trans_employee_combobox.grid(row=2, column=1, padx=5, pady=5)

        self.trans_supplier_label = ttk.Label(form_frame, text="المورد:")
        self.trans_supplier_label.grid(row=3, column=0, padx=5, pady=5, sticky='w')
        self.trans_supplier_combobox = ttk.Combobox(form_frame, state="readonly", width=37)
        self.trans_supplier_combobox.grid(row=3, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="ملاحظات/السبب:").grid(row=4, column=0, padx=5, pady=5, sticky='w')
        self.trans_notes_entry = ttk.Entry(form_frame, width=40)
        self.trans_notes_entry.grid(row=4, column=1, padx=5, pady=5)
        
        ttk.Button(form_frame, text="تسجيل الحركة", command=self.record_transaction).grid(row=5, column=0, columnspan=2, pady=10)

        history_frame = ttk.LabelFrame(self.transactions_frame, text="سجل الحركات")
        history_frame.pack(padx=10, pady=10, fill='both', expand=True)

        self.transactions_tree = ttk.Treeview(history_frame, columns=('ID', 'Date', 'Type', 'Item', 'Qty', 'Employee', 'Supplier', 'Notes'), show='headings')
        self.transactions_tree.heading('ID', text='الرقم')
        self.transactions_tree.heading('Date', text='التاريخ')
        self.transactions_tree.heading('Type', text='النوع')
        self.transactions_tree.heading('Item', text='المادة')
        self.transactions_tree.heading('Qty', text='الكمية')
        self.transactions_tree.heading('Employee', text='الموظف')
        self.transactions_tree.heading('Supplier', text='المورد')
        self.transactions_tree.heading('Notes', text='ملاحظات')

        self.transactions_tree.column('ID', width=40, anchor='center')
        self.transactions_tree.column('Qty', width=60, anchor='center')
        self.transactions_tree.pack(fill='both', expand=True)
        
        self.refresh_comboboxes()
        self.refresh_transactions_tree()

    def toggle_supplier_field(self):
        if self.transaction_type_var.get() == "RECEIVE":
            self.trans_supplier_label.grid()
            self.trans_supplier_combobox.grid()
        else:
            self.trans_supplier_label.grid_remove()
            self.trans_supplier_combobox.grid_remove()

    def refresh_comboboxes(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        # Refresh Items
        cursor.execute("SELECT name FROM items ORDER BY name")
        items = [row[0] for row in cursor.fetchall()]
        self.trans_item_combobox['values'] = items
        # Refresh Employees
        cursor.execute("SELECT name FROM employees ORDER BY name")
        employees = [row[0] for row in cursor.fetchall()]
        self.trans_employee_combobox['values'] = employees
        # Refresh Suppliers
        cursor.execute("SELECT name FROM suppliers ORDER BY name")
        suppliers = [row[0] for row in cursor.fetchall()]
        self.trans_supplier_combobox['values'] = suppliers
        conn.close()

    def record_transaction(self):
        item_name = self.trans_item_combobox.get()
        qty_str = self.trans_qty_entry.get()
        employee_name = self.trans_employee_combobox.get()
        supplier_name = self.trans_supplier_combobox.get() if self.transaction_type_var.get() == "RECEIVE" else None
        notes = self.trans_notes_entry.get()

        if not all([item_name, qty_str, employee_name]):
            messagebox.showerror("خطأ", "حقول المادة، الكمية، والموظف مطلوبة.")
            return
        
        if self.transaction_type_var.get() == "RECEIVE" and not supplier_name:
            messagebox.showerror("خطأ", "حقل المورد مطلوب لحركة الاستلام.")
            return

        try:
            qty = int(qty_str)
            if qty <= 0:
                raise ValueError("الكمية يجب أن تكون رقماً موجباً.")
        except ValueError:
            messagebox.showerror("خطأ", "الكمية يجب أن تكون رقماً صحيحاً موجباً.")
            return

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM items WHERE name=?", (item_name,))
        item_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM employees WHERE name=?", (employee_name,))
        employee_id = cursor.fetchone()[0]
        
        supplier_id = None
        if supplier_name:
            cursor.execute("SELECT id FROM suppliers WHERE name=?", (supplier_name,))
            supplier_id = cursor.fetchone()[0]

        cursor.execute("SELECT quantity FROM items WHERE id=?", (item_id,))
        current_qty = cursor.fetchone()[0]

        if self.transaction_type_var.get() == "RECEIVE":
            new_qty = current_qty + qty
        else: # ISSUE
            if qty > current_qty:
                messagebox.showerror("خطأ", f"الكمية المطلوبة غير متوفرة. المتوفر: {current_qty}")
                conn.close()
                return
            new_qty = current_qty - qty
        
        cursor.execute("UPDATE items SET quantity=? WHERE id=?", (new_qty, item_id))

        transaction_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO transactions (item_id, quantity, transaction_type, transaction_date, employee_id, supplier_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (item_id, qty, self.transaction_type_var.get(), transaction_date, employee_id, supplier_id, notes))
        
        conn.commit()
        conn.close()

        messagebox.showinfo("نجاح", "تم تسجيل الحركة بنجاح.")
        self.trans_qty_entry.delete(0, tk.END)
        self.trans_notes_entry.delete(0, tk.END)
        self.refresh_items_tree()
        self.refresh_transactions_tree()
        if hasattr(self, 'activity_tree'):
            self.update_recent_activity()


    def refresh_transactions_tree(self):
        for i in self.transactions_tree.get_children():
            self.transactions_tree.delete(i)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        query = '''
        SELECT 
            t.id, t.transaction_date, t.transaction_type, 
            i.name AS item_name, t.quantity,
            e.name AS employee_name,
            s.name AS supplier_name,
            t.notes
        FROM transactions t
        JOIN items i ON t.item_id = i.id
        JOIN employees e ON t.employee_id = e.id
        LEFT JOIN suppliers s ON t.supplier_id = s.id
        ORDER BY t.transaction_date DESC
        '''
        cursor.execute(query)
        for row in cursor.fetchall():
            type_ar = "استلام" if row[2] == 'RECEIVE' else "تسليم"
            self.transactions_tree.insert('', 'end', values=(row[0], row[1], type_ar, row[3], row[4], row[5], row[6] or '-', row[7] or '-'))
        conn.close()


# --- Main Execution ---
if __name__ == "__main__":
    setup_database()
    app = InventoryApp()
    app.mainloop()