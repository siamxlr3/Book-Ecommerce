import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "ecommerce.db")

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def verify_db():
    with db() as con:
        required = {"users", "admins", "books", "cart", "orders"}
        existing = {r["name"] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = required - existing
        if missing:
            raise RuntimeError("Database is missing tables: " + ", ".join(sorted(missing)) +
                               ". Use the original ecommerce.db or run setup.sql on a backup.")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("E-Commerce Book Management System")
        self.geometry("1100x700")
        self.minsize(900, 580)
        self.configure(bg="#f1f5f9")
        self.user = None
        self.role = None
        style = ttk.Style(self)
        try: style.theme_use("clam")
        except tk.TclError: pass
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.configure("TButton", padding=7)
        verify_db()
        self.home()

    def clear(self):
        for w in self.winfo_children(): w.destroy()

    def header(self, title, subtitle="E-Commerce Book Management System"):
        h=tk.Frame(self,bg="#172554",padx=24,pady=18); h.pack(fill="x")
        tk.Label(h,text=title,bg="#172554",fg="white",font=("Segoe UI",21,"bold")).pack(anchor="w")
        tk.Label(h,text=subtitle,bg="#172554",fg="#cbd5e1",font=("Segoe UI",10)).pack(anchor="w",pady=(4,0))

    def home(self):
        self.user=self.role=None
        self.clear(); self.header("BOOKSTORE","A desktop book shopping and inventory application")
        body=tk.Frame(self,bg="#f1f5f9",padx=35,pady=35); body.pack(fill="both",expand=True)
        tk.Label(body,text="Welcome to E-Commerce Book",bg="#f1f5f9",fg="#172554",
                 font=("Segoe UI",20,"bold")).pack(pady=(30,8))
        tk.Label(body,text="Shop books, manage your cart, and track orders.",bg="#f1f5f9",
                 fg="#475569",font=("Segoe UI",11)).pack(pady=(0,25))
        for text,cmd in [("User Login",self.user_login),("Create Account",self.register),
                         ("Forgot Password",self.forgot_password),("Admin Login",self.admin_login),
                         ("Exit",self.destroy)]:
            ttk.Button(body,text=text,command=cmd,width=30).pack(pady=5)

    def form(self,title,fields,submit_text,callback):
        win=tk.Toplevel(self); win.title(title); win.configure(bg="#f8fafc")
        win.transient(self); win.grab_set()
        f=tk.Frame(win,bg="#f8fafc",padx=24,pady=22); f.pack()
        tk.Label(f,text=title,bg="#f8fafc",fg="#172554",font=("Segoe UI",16,"bold")).grid(row=0,column=0,columnspan=2,sticky="w",pady=(0,14))
        entries={}
        for i,(key,label,secret) in enumerate(fields,1):
            tk.Label(f,text=label,bg="#f8fafc").grid(row=i,column=0,sticky="w",padx=(0,14),pady=7)
            e=ttk.Entry(f,width=34,show="*" if secret else "")
            e.grid(row=i,column=1,pady=7); entries[key]=e
        def go():
            values={k:e.get().strip() for k,e in entries.items()}
            if any(not v for v in values.values()):
                messagebox.showwarning("Missing information","Please complete all fields.",parent=win); return
            callback(values,win)
        ttk.Button(f,text=submit_text,command=go).grid(row=len(fields)+1,column=0,columnspan=2,sticky="ew",pady=(14,0))
        win.bind("<Return>",lambda e:go()); entries[fields[0][0]].focus_set()

    def register(self):
        def create(v,w):
            try:
                with db() as c:
                    c.execute("INSERT INTO users(username,email,password) VALUES(?,?,?)",(v["username"],v["email"],v["password"]))
                messagebox.showinfo("Registered","Account created successfully.",parent=w); w.destroy()
            except sqlite3.IntegrityError:
                messagebox.showerror("Registration failed","Username already exists.",parent=w)
        self.form("Create Account",[("username","Username",False),("email","Email",False),("password","Password",True)],"Register",create)

    def user_login(self):
        def login(v,w):
            with db() as c: row=c.execute("SELECT username FROM users WHERE username=? AND password=?",(v["username"],v["password"])).fetchone()
            if row:
                self.user=row["username"]; self.role="user"; w.destroy(); self.user_dashboard()
            else: messagebox.showerror("Login failed","Incorrect username or password.",parent=w)
        self.form("User Login",[("username","Username",False),("password","Password",True)],"Login",login)

    def admin_login(self):
        def login(v,w):
            with db() as c: row=c.execute("SELECT username FROM admins WHERE username=? AND password=?",(v["username"],v["password"])).fetchone()
            if row:
                self.user=row["username"]; self.role="admin"; w.destroy(); self.admin_dashboard()
            else: messagebox.showerror("Login failed","Incorrect admin username or password.",parent=w)
        self.form("Admin Login",[("username","Admin username",False),("password","Password",True)],"Login",login)

    def forgot_password(self):
        def reset(v,w):
            with db() as c:
                row=c.execute("SELECT id FROM users WHERE username=? AND email=?",(v["username"],v["email"])).fetchone()
                if not row:
                    messagebox.showerror("Not found","Username and email did not match.",parent=w); return
                c.execute("UPDATE users SET password=? WHERE id=?",(v["new_password"],row["id"]))
            messagebox.showinfo("Password reset","Password updated. Please log in.",parent=w); w.destroy()
        self.form("Reset Password",[("username","Username",False),("email","Registered email",False),("new_password","New password",True)],"Reset Password",reset)

    def toolbar(self,title,subtitle):
        self.clear(); self.header(title,subtitle)
        bar=tk.Frame(self,bg="#e2e8f0",padx=12,pady=8); bar.pack(fill="x")
        ttk.Button(bar,text="Home / Log out",command=self.home).pack(side="right")

    def table(self,parent,columns,labels,widths):
        t=ttk.Treeview(parent,columns=columns,show="headings",selectmode="browse")
        for c,l,w in zip(columns,labels,widths):
            t.heading(c,text=l); t.column(c,width=w,anchor="w" if c in ("title","author","book_name","delivery_address","username") else "center")
        t.pack(fill="both",expand=True); return t

    def user_dashboard(self):
        self.toolbar("Book Catalogue",f"Logged in as {self.user} — add books to your cart and checkout")
        body=tk.Frame(self,bg="#f1f5f9",padx=18,pady=16); body.pack(fill="both",expand=True)
        search=tk.Frame(body,bg="#f1f5f9"); search.pack(fill="x",pady=(0,10))
        tk.Label(search,text="Search title/author:",bg="#f1f5f9").pack(side="left")
        q=ttk.Entry(search,width=35); q.pack(side="left",padx=8)
        t=self.table(body,("id","title","author","price","quantity"),("ID","Book Title","Author","Price (৳)","Stock"),(60,330,230,120,100))
        def load():
            t.delete(*t.get_children())
            term=q.get().strip()
            with db() as c:
                rows=c.execute("SELECT id,title,author,price,quantity FROM books WHERE title LIKE ? OR author LIKE ? ORDER BY title",
                               (f"%{term}%",f"%{term}%")).fetchall()
            for r in rows: t.insert("","end",values=(r["id"],r["title"],r["author"],f'{r["price"]:.2f}',r["quantity"]))
        q.bind("<KeyRelease>",lambda e:load()); load()
        buttons=tk.Frame(body,bg="#f1f5f9",pady=12); buttons.pack(fill="x")
        ttk.Button(buttons,text="Add Selected to Cart",command=lambda:self.add_cart(t)).pack(side="left",padx=(0,8))
        ttk.Button(buttons,text="View Cart / Checkout",command=self.view_cart).pack(side="left",padx=8)
        ttk.Button(buttons,text="My Order History",command=self.order_history).pack(side="right")

    def add_cart(self,t):
        s=t.selection()
        if not s: messagebox.showwarning("Select book","Select a book first."); return
        v=t.item(s[0],"values"); book_id=int(v[0])
        with db() as c:
            b=c.execute("SELECT * FROM books WHERE id=?",(book_id,)).fetchone()
            if not b: messagebox.showerror("Not found","Book not found."); return
            if b["quantity"]<1: messagebox.showwarning("Out of stock","This book is out of stock."); return
            c.execute("INSERT INTO cart(username,book_id,book_name,price) VALUES(?,?,?,?)",
                      (self.user,b["id"],b["title"],b["price"]))
        messagebox.showinfo("Cart","Book added to your cart.")

    def view_cart(self):
        self.toolbar("Shopping Cart",f"Cart for {self.user}")
        body=tk.Frame(self,bg="#f1f5f9",padx=18,pady=16); body.pack(fill="both",expand=True)
        t=self.table(body,("id","book_id","book_name","price"),("Cart ID","Book ID","Book","Price (৳)"),(90,90,480,150))
        with db() as c: rows=c.execute("SELECT id,book_id,book_name,price FROM cart WHERE username=? ORDER BY id",(self.user,)).fetchall()
        for r in rows: t.insert("","end",values=(r["id"],r["book_id"],r["book_name"],f'{r["price"]:.2f}'))
        subtotal=sum(float(r["price"]) for r in rows)
        rate=.20 if subtotal>=1999 else .10 if subtotal>=1499 else .05 if subtotal>=999 else 0
        total=subtotal*(1-rate)
        tk.Label(body,text=f"Subtotal: ৳{subtotal:.2f}    Discount: {rate*100:.0f}%    Total: ৳{total:.2f}",
                 bg="#f1f5f9",fg="#172554",font=("Segoe UI",13,"bold")).pack(anchor="e",pady=12)
        row=tk.Frame(body,bg="#f1f5f9"); row.pack(fill="x")
        def remove():
            s=t.selection()
            if not s: messagebox.showwarning("Select item","Select a cart item."); return
            cid=int(t.item(s[0],"values")[0])
            with db() as c: c.execute("DELETE FROM cart WHERE id=? AND username=?",(cid,self.user))
            self.view_cart()
        ttk.Button(row,text="Remove Selected",command=remove).pack(side="left")
        ttk.Button(row,text="Checkout All",command=lambda:self.checkout(rows,subtotal,rate)).pack(side="right")
        ttk.Button(row,text="Back to Books",command=self.user_dashboard).pack(side="right",padx=8)

    def checkout(self,rows,subtotal,rate):
        if not rows: messagebox.showinfo("Empty cart","Your cart is empty."); return
        address=simpledialog.askstring("Delivery information","Delivery address:",parent=self)
        if not address or not address.strip(): return
        phone=simpledialog.askstring("Delivery information","Phone number:",parent=self)
        if not phone or not phone.strip(): return
        if not messagebox.askyesno("Confirm checkout",f"Subtotal: ৳{subtotal:.2f}\nDiscount: {rate*100:.0f}%\nTotal: ৳{subtotal*(1-rate):.2f}\n\nPlace order?",parent=self): return
        today=datetime.now().strftime("%d-%m-%Y")
        try:
            with db() as c:
                # Check stock for every cart item before committing any order.
                for r in rows:
                    b=c.execute("SELECT quantity FROM books WHERE id=?",(r["book_id"],)).fetchone()
                    if not b or b["quantity"] < 1:
                        raise ValueError(f'Not enough stock for "{r["book_name"]}". Remove it or contact admin.')
                for r in rows:
                    discounted=float(r["price"])*(1-rate)
                    c.execute("""INSERT INTO orders(username,book_id,book_name,price,order_date,delivery_address,phone_number,status)
                                 VALUES(?,?,?,?,?,?,?,'Pending')""",
                              (self.user,r["book_id"],r["book_name"],discounted,today,address.strip(),phone.strip()))
                    c.execute("UPDATE books SET quantity=quantity-1 WHERE id=?",(r["book_id"],))
                c.execute("DELETE FROM cart WHERE username=?",(self.user,))
            messagebox.showinfo("Order placed","Checkout complete. Your orders are now Pending.")
            self.order_history()
        except ValueError as e: messagebox.showerror("Stock issue",str(e))
        except sqlite3.Error as e: messagebox.showerror("Database error",str(e))

    def order_history(self):
        self.toolbar("Order History",f"Orders for {self.user}")
        body=tk.Frame(self,bg="#f1f5f9",padx=18,pady=16); body.pack(fill="both",expand=True)
        t=self.table(body,("id","book_name","price","order_date","status","phone_number","delivery_address"),
                     ("Order ID","Book","Price (৳)","Date","Status","Phone","Delivery Address"),
                     (70,210,100,110,110,140,270))
        with db() as c: rows=c.execute("SELECT id,book_name,price,order_date,status,phone_number,delivery_address FROM orders WHERE username=? ORDER BY id DESC",(self.user,)).fetchall()
        for r in rows: t.insert("","end",values=(r["id"],r["book_name"],f'{r["price"] or 0:.2f}',r["order_date"],r["status"] or "Pending",r["phone_number"],r["delivery_address"]))
        ttk.Button(body,text="Back to Books",command=self.user_dashboard).pack(anchor="w",pady=12)

    def admin_dashboard(self):
        self.toolbar("Admin Dashboard",f"Administrator: {self.user} — inventory and order management")
        body=tk.Frame(self,bg="#f1f5f9",padx=16,pady=14); body.pack(fill="both",expand=True)
        tabs=ttk.Notebook(body); tabs.pack(fill="both",expand=True)
        books_tab=tk.Frame(tabs,padx=10,pady=10); orders_tab=tk.Frame(tabs,padx=10,pady=10)
        tabs.add(books_tab,text="Book Inventory"); tabs.add(orders_tab,text="Manage Orders")
        bt=self.table(books_tab,("id","title","author","price","quantity"),("ID","Title","Author","Price (৳)","Stock"),(60,300,220,120,90))
        def load_books():
            bt.delete(*bt.get_children())
            with db() as c: rows=c.execute("SELECT id,title,author,price,quantity FROM books ORDER BY id").fetchall()
            for r in rows: bt.insert("","end",values=(r["id"],r["title"],r["author"],f'{r["price"]:.2f}',r["quantity"]))
        def book_form(edit=False):
            sel=bt.selection()
            if edit and not sel: messagebox.showwarning("Select book","Select a book to edit."); return
            old=bt.item(sel[0],"values") if sel else None
            w=tk.Toplevel(self); w.title("Edit Book" if edit else "Add Book"); w.transient(self); w.grab_set()
            f=tk.Frame(w,padx=18,pady=18); f.pack()
            fields=[("title","Title"),("author","Author"),("price","Price"),("quantity","Quantity")]
            es={}
            for i,(key,label) in enumerate(fields):
                tk.Label(f,text=label).grid(row=i,column=0,sticky="w",padx=(0,12),pady=6)
                e=ttk.Entry(f,width=35); e.grid(row=i,column=1,pady=6); es[key]=e
                if old: e.insert(0,str(old[i+1]))
            def save():
                v={k:e.get().strip() for k,e in es.items()}
                try:
                    price=float(v["price"]); qty=int(v["quantity"])
                    if not v["title"] or not v["author"] or price<0 or qty<0: raise ValueError
                    with db() as c:
                        if edit: c.execute("UPDATE books SET title=?,author=?,price=?,quantity=? WHERE id=?",(v["title"],v["author"],price,qty,int(old[0])))
                        else: c.execute("INSERT INTO books(title,author,price,quantity) VALUES(?,?,?,?)",(v["title"],v["author"],price,qty))
                    w.destroy(); load_books()
                except ValueError: messagebox.showerror("Invalid input","Enter a title, author, non-negative price, and whole-number quantity.",parent=w)
            ttk.Button(f,text="Save",command=save).grid(row=4,column=0,columnspan=2,sticky="ew",pady=(12,0))
        def delete_book():
            sel=bt.selection()
            if not sel: messagebox.showwarning("Select book","Select a book to delete."); return
            vals=bt.item(sel[0],"values")
            if messagebox.askyesno("Confirm","Delete book "+str(vals[1])+"?",parent=self):
                with db() as c: c.execute("DELETE FROM books WHERE id=?",(int(vals[0]),))
                load_books()
        bbar=tk.Frame(books_tab); bbar.pack(fill="x",pady=10)
        ttk.Button(bbar,text="Add Book",command=lambda:book_form(False)).pack(side="left",padx=4)
        ttk.Button(bbar,text="Edit Selected",command=lambda:book_form(True)).pack(side="left",padx=4)
        ttk.Button(bbar,text="Delete Selected",command=delete_book).pack(side="left",padx=4)
        ttk.Button(bbar,text="Refresh",command=load_books).pack(side="right")
        load_books()

        ot=self.table(orders_tab,("id","username","book_name","price","order_date","status","phone_number","delivery_address"),
                      ("Order ID","User","Book","Price","Date","Status","Phone","Address"),
                      (70,120,180,90,100,100,130,260))
        def load_orders():
            ot.delete(*ot.get_children())
            with db() as c: rows=c.execute("SELECT id,username,book_name,price,order_date,status,phone_number,delivery_address FROM orders ORDER BY id DESC").fetchall()
            for r in rows: ot.insert("","end",values=(r["id"],r["username"],r["book_name"],f'{r["price"] or 0:.2f}',r["order_date"],r["status"] or "Pending",r["phone_number"],r["delivery_address"]))
        def change_status():
            sel=ot.selection()
            if not sel: messagebox.showwarning("Select order","Select an order first."); return
            oid=int(ot.item(sel[0],"values")[0])
            w=tk.Toplevel(self); w.title("Update Order Status"); w.transient(self); w.grab_set()
            f=tk.Frame(w,padx=18,pady=18); f.pack()
            tk.Label(f,text=f"Order #{oid} status:").pack(anchor="w",pady=(0,8))
            choice=tk.StringVar(value="Pending")
            ttk.Combobox(f,textvariable=choice,values=["Pending","Delivered","Cancelled"],state="readonly").pack(fill="x")
            def save():
                if choice.get() not in ("Pending","Delivered","Cancelled"): return
                with db() as c: c.execute("UPDATE orders SET status=? WHERE id=?",(choice.get(),oid))
                w.destroy(); load_orders()
            ttk.Button(f,text="Save Status",command=save).pack(fill="x",pady=(12,0))
        obar=tk.Frame(orders_tab); obar.pack(fill="x",pady=10)
        ttk.Button(obar,text="Update Status",command=change_status).pack(side="left")
        ttk.Button(obar,text="Refresh Orders",command=load_orders).pack(side="left",padx=8)
        load_orders()

if __name__ == "__main__":
    try:
        app=App()
        app.mainloop()
    except Exception as exc:
        root=tk.Tk(); root.withdraw()
        messagebox.showerror("Startup error",f"Could not start the application:\n{exc}")
        root.destroy()
