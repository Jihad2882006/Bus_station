#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
محطة إكسبريس | Express Bus System - Backend Server
خادم الباك إند المتكامل وقاعدة البيانات (Python + SQLite)
يقدم واجهة برمجية كاملة (RESTful API) ويخدم ملفات الفرونت إند.
"""

import sys
import os
import json
import sqlite3
import urllib.parse
import zipfile
import io
import xml.sax.saxutils
import csv
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime, timedelta

PORT = 8080
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bus_station.db')
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_FILE = os.path.join(STATIC_DIR, 'registered_users.xlsx')
CSV_FILE = os.path.join(STATIC_DIR, 'registered_users.csv')
# كود الأمان وتفويض إدارة المحطة (سري ومخصص لمدير المحطة فقط)
ADMIN_SECURITY_PASSCODE = "ADMIN@STATION2026"

# ==================== 1. إدارة قاعدة البيانات (SQLite Database) ====================
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # جدول المستخدمين
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name TEXT,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        phone TEXT,
        address TEXT,
        password TEXT NOT NULL,
        role TEXT NOT NULL, -- customer, driver, admin
        license_number TEXT,
        bus_number TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # ترقية تلقائية للأعمدة إذا كان الجدول موجوداً مسبقاً (Database Migration)
    cursor.execute("PRAGMA table_info(users)")
    cols = [col[1] for col in cursor.fetchall()]
    if 'first_name' not in cols: cursor.execute("ALTER TABLE users ADD COLUMN first_name TEXT")
    if 'last_name' not in cols: cursor.execute("ALTER TABLE users ADD COLUMN last_name TEXT")
    if 'address' not in cols: cursor.execute("ALTER TABLE users ADD COLUMN address TEXT")
    if 'license_number' not in cols: cursor.execute("ALTER TABLE users ADD COLUMN license_number TEXT")
    if 'bus_number' not in cols: cursor.execute("ALTER TABLE users ADD COLUMN bus_number TEXT")


    # جدول السائقين والأسطول
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS drivers (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        bus_info TEXT NOT NULL,
        rating REAL DEFAULT 4.9,
        is_active INTEGER DEFAULT 1
    )
    ''')

    # جدول الرحلات
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trips (
        id TEXT PRIMARY KEY,
        from_city TEXT NOT NULL,
        from_station TEXT NOT NULL,
        to_city TEXT NOT NULL,
        to_station TEXT NOT NULL,
        departure_time TEXT NOT NULL,
        departure_time_label TEXT NOT NULL,
        arrival_time_label TEXT NOT NULL,
        duration TEXT NOT NULL,
        trip_date TEXT NOT NULL,
        price INTEGER NOT NULL,
        bus_class TEXT NOT NULL,
        bus_class_label TEXT NOT NULL,
        bus_number TEXT NOT NULL,
        driver_name TEXT NOT NULL,
        total_seats INTEGER DEFAULT 28,
        status TEXT DEFAULT 'ready',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # جدول الحجوزات والدفع
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bookings (
        pnr TEXT PRIMARY KEY,
        trip_id TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        national_id TEXT,
        seats TEXT NOT NULL, -- JSON string e.g. "[1, 2]"
        total_amount INTEGER NOT NULL,
        payment_method TEXT NOT NULL, -- card, wallet, cash
        payment_status TEXT NOT NULL, -- paid, pending_cash
        boarded INTEGER DEFAULT 0, -- 0: لم يصعد, 1: صعد للحافلة
        booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (trip_id) REFERENCES trips (id)
    )
    ''')

    conn.commit()

    # إضافة بيانات افتراضية إذا كانت الجداول فارغة
    cursor.execute('SELECT COUNT(*) FROM trips')
    if cursor.fetchone()[0] == 0:
        seed_default_data(cursor, conn)

    conn.close()
    print("✅ تم تجهيز قاعدة بيانات SQLite بنجاح:", DB_FILE)

def seed_default_data(cursor, conn):
    today = datetime.now().strftime('%Y-%m-%d')

    # سائقين والأسطول
    drivers = [
        ('DRV-101', 'محمود حسن السعيد', '01099887766', 'أتوبيس 705 (مرسيدس سوبر جيت)', 4.9, 1),
        ('DRV-102', 'إبراهيم كمال الدين', '01122334455', 'أتوبيس 910 (مان ترانس)', 4.8, 1),
        ('DRV-103', 'خالد عبد العزيز', '01233445566', 'أتوبيس 302 (دايو كلاسيك)', 4.7, 1),
        ('DRV-104', 'سامح فاروق الشريف', '01555667788', 'أتوبيس 441 (مرسيدس توريزمو)', 4.9, 1)
    ]
    cursor.executemany('INSERT OR IGNORE INTO drivers (id, name, phone, bus_info, rating, is_active) VALUES (?, ?, ?, ?, ?, ?)', drivers)

    # رحلات تغطي جميع محافظات مصر
    trips = [
        ('EX-804', 'القاهرة', 'موقف رمسيس / الترجمان', 'الإسكندرية', 'موقف محرم بك', '14:30', '02:30 م', '05:30 م', '3 ساعات', today, 180, 'VIP', 'VIP فاخر', 'أتوبيس 705 (مرسيدس سوبر جيت)', 'محمود حسن السعيد', 28, 'ready'),
        ('EX-805', 'القاهرة', 'موقف رمسيس', 'شرم الشيخ', 'موقف الرويسات', '07:00', '07:00 ص', '01:30 م', '6.5 ساعات', today, 320, 'VIP', 'VIP فاخر', 'أتوبيس 910 (مان ترانس)', 'إبراهيم كمال الدين', 28, 'ready'),
        ('EX-806', 'الإسكندرية', 'موقف محرم بك', 'المنصورة', 'المحطة المركزية', '10:00', '10:00 ص', '01:00 م', '3 ساعات', today, 120, 'Standard', 'اقتصادي مريح', 'أتوبيس 302 (دايو كلاسيك)', 'خالد عبد العزيز', 28, 'ready'),
        ('EX-807', 'القاهرة', 'موقف رمسيس', 'الغردقة', 'محطة الدهار', '23:30', '11:30 م', '05:30 ص', '6 ساعات', today, 290, 'Business', 'رجال أعمال', 'أتوبيس 441 (مرسيدس توريزمو)', 'سامح فاروق الشريف', 28, 'ready'),
        ('EX-808', 'القاهرة', 'موقف رمسيس', 'أسوان', 'موقف الأقاليم', '18:00', '06:00 م', '07:00 ص', '13 ساعة', today, 450, 'VIP', 'VIP فاخر', 'أتوبيس 705 (مرسيدس سوبر جيت)', 'محمود حسن السعيد', 28, 'ready'),
        ('EX-809', 'القاهرة', 'موقف الترجمان', 'بورسعيد', 'المحطة المركزية ببورسعيد', '08:00', '08:00 ص', '11:00 ص', '3 ساعات', today, 140, 'VIP', 'VIP فاخر', 'أتوبيس 910 (مان ترانس)', 'إبراهيم كمال الدين', 28, 'ready'),
        ('EX-810', 'القاهرة', 'موقف عبود', 'طنطا', 'موقف الجلاء بطنطا', '09:30', '09:30 ص', '11:00 ص', '1.5 ساعة', today, 80, 'Standard', 'اقتصادي مريح', 'أتوبيس 302 (دايو كلاسيك)', 'خالد عبد العزيز', 28, 'ready'),
        ('EX-811', 'القاهرة', 'موقف رمسيس', 'الإسماعيلية', 'موقف الأقاليم الجديد', '11:00', '11:00 ص', '01:00 م', 'ساعتان', today, 95, 'Business', 'رجال أعمال', 'أتوبيس 441 (مرسيدس توريزمو)', 'سامح فاروق الشريف', 28, 'ready'),
        ('EX-812', 'القاهرة', 'موقف المرج', 'السويس', 'موقف السويس الرئيسي', '13:00', '01:00 م', '03:00 م', 'ساعتان', today, 90, 'Standard', 'اقتصادي مريح', 'أتوبيس 302 (دايو كلاسيك)', 'خالد عبد العزيز', 28, 'ready'),
        ('EX-813', 'القاهرة', 'موقف رمسيس', 'مرسى مطروح', 'موقف مطروح المركزي', '06:30', '06:30 ص', '12:00 م', '5.5 ساعات', today, 260, 'VIP', 'VIP فاخر', 'أتوبيس 705 (مرسيدس سوبر جيت)', 'محمود حسن السعيد', 28, 'ready'),
        ('EX-814', 'القاهرة', 'موقف المنيب', 'الفيوم', 'موقف الفيوم العام', '07:30', '07:30 ص', '09:00 ص', '1.5 ساعة', today, 65, 'Standard', 'اقتصادي مريح', 'أتوبيس 302 (دايو كلاسيك)', 'خالد عبد العزيز', 28, 'ready'),
        ('EX-815', 'القاهرة', 'موقف المنيب', 'بني سويف', 'الموقف العمومي ببني سويف', '08:30', '08:30 ص', '10:30 ص', 'ساعتان', today, 85, 'Standard', 'اقتصادي مريح', 'أتوبيس 302 (دايو كلاسيك)', 'سامح فاروق الشريف', 28, 'ready'),
        ('EX-816', 'القاهرة', 'موقف المنيب', 'المنيا', 'موقف المنيا الرئيسي', '10:00', '10:00 ص', '01:30 م', '3.5 ساعات', today, 140, 'Business', 'رجال أعمال', 'أتوبيس 441 (مرسيدس توريزمو)', 'إبراهيم كمال الدين', 28, 'ready'),
        ('EX-817', 'القاهرة', 'موقف المنيب', 'أسيوط', 'موقف المعلمين الجديد بأسيوط', '12:00', '12:00 م', '05:00 م', '5 ساعات', today, 210, 'VIP', 'VIP فاخر', 'أتوبيس 705 (مرسيدس سوبر جيت)', 'محمود حسن السعيد', 28, 'ready'),
        ('EX-818', 'القاهرة', 'موقف المنيب', 'سوهاج', 'موقف سوهاج الإقليمي', '14:00', '02:00 م', '08:30 م', '6.5 ساعات', today, 250, 'VIP', 'VIP فاخر', 'أتوبيس 910 (مان ترانس)', 'سامح فاروق الشريف', 28, 'ready'),
        ('EX-819', 'القاهرة', 'موقف المنيب', 'الأقصر', 'موقف الأقصر الدولي', '19:00', '07:00 م', '05:00 ص', '10 ساعات', today, 380, 'VIP', 'VIP فاخر', 'أتوبيس 705 (مرسيدس سوبر جيت)', 'محمود حسن السعيد', 28, 'ready'),
        ('EX-820', 'القاهرة', 'موقف المنيب', 'قنا', 'موقف قنا العام', '16:30', '04:30 م', '01:30 ص', '9 ساعات', today, 330, 'Business', 'رجال أعمال', 'أتوبيس 441 (مرسيدس توريزمو)', 'إبراهيم كمال الدين', 28, 'ready'),
        ('EX-821', 'القاهرة', 'موقف عبود', 'دمياط', 'موقف دمياط / رأس البر', '09:00', '09:00 ص', '12:30 م', '3.5 ساعات', today, 130, 'VIP', 'VIP فاخر', 'أتوبيس 910 (مان ترانس)', 'خالد عبد العزيز', 28, 'ready'),
        ('EX-822', 'القاهرة', 'موقف عبود', 'كفر الشيخ', 'الموقف العمومي بكفر الشيخ', '10:30', '10:30 ص', '01:00 م', '2.5 ساعة', today, 90, 'Standard', 'اقتصادي مريح', 'أتوبيس 302 (دايو كلاسيك)', 'سامح فاروق الشريف', 28, 'ready'),
        ('EX-823', 'القاهرة', 'موقف عبود', 'الزقازيق', 'موقف الأحرار بالشرقية', '08:00', '08:00 ص', '09:30 ص', '1.5 ساعة', today, 60, 'Standard', 'اقتصادي مريح', 'أتوبيس 302 (دايو كلاسيك)', 'خالد عبد العزيز', 28, 'ready'),
        ('EX-824', 'القاهرة', 'موقف عبود', 'شبين الكوم', 'موقف شبين الكوم بالمنوفية', '08:30', '08:30 ص', '10:00 ص', '1.5 ساعة', today, 55, 'Standard', 'اقتصادي مريح', 'أتوبيس 302 (دايو كلاسيك)', 'سامح فاروق الشريف', 28, 'ready'),
        ('EX-825', 'القاهرة', 'موقف رمسيس', 'دهب', 'موقف دهب المركزي', '22:00', '10:00 م', '06:30 ص', '8.5 ساعات', today, 340, 'VIP', 'VIP فاخر', 'أتوبيس 705 (مرسيدس سوبر جيت)', 'محمود حسن السعيد', 28, 'ready')
    ]
    cursor.executemany('''
    INSERT OR IGNORE INTO trips (id, from_city, from_station, to_city, to_station, departure_time, departure_time_label,
                      arrival_time_label, duration, trip_date, price, bus_class, bus_class_label, bus_number, driver_name, total_seats, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', trips)

    conn.commit()
    conn.close()

    # مزامنة وتحديث ملفات الإكسيل (Excel & CSV) عند بدء تشغيل الخادم
    sync_excel_files()





# ==================== أدوات معالجة النصوص والأرقام ====================
def normalize_input(text):
    if not text:
        return ''
    text = str(text).strip()
    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
    english_digits = '0123456789'
    tr = str.maketrans(arabic_digits, english_digits)
    return text.translate(tr)

def normalize_phone(phone):
    p = normalize_input(phone).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if p.startswith('+20'):
        p = '0' + p[3:]
    elif p.startswith('0020'):
        p = '0' + p[4:]
    elif p.startswith('20') and len(p) == 12:
        p = '0' + p[2:]
    return p


# ==================== نظام تصدير ومزامنة ملفات الإكسيل (Excel Live Sync) ====================
def escape_xml(val):
    if val is None:
        return ''
    return xml.sax.saxutils.escape(str(val))

def col_letter(col_idx):
    res = ''
    while col_idx > 0:
        col_idx, rem = divmod(col_idx - 1, 26)
        res = chr(65 + rem) + res
    return res

def build_sheet_xml(headers, rows):
    xml = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>']
    xml.append('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">')
    xml.append('<sheetViews><sheetView tabSelected="1" workbookViewId="0" rightToLeft="1"/></sheetViews>')
    xml.append('<sheetData>')
    
    # صف العناوين الرئيسية
    xml.append('<row r="1">')
    for c_idx, h in enumerate(headers, 1):
        cell_ref = f"{col_letter(c_idx)}1"
        xml.append(f'<c r="{cell_ref}" t="inlineStr" s="1"><is><t>{escape_xml(h)}</t></is></c>')
    xml.append('</row>')
    
    # صفوف البيانات
    for r_idx, row in enumerate(rows, 2):
        xml.append(f'<row r="{r_idx}">')
        for c_idx, val in enumerate(row, 1):
            cell_ref = f"{col_letter(c_idx)}{r_idx}"
            xml.append(f'<c r="{cell_ref}" t="inlineStr" s="0"><is><t>{escape_xml(val)}</t></is></c>')
        xml.append('</row>')
        
    xml.append('</sheetData>')
    xml.append('</worksheet>')
    return ''.join(xml)

def generate_excel_bytes(sheets):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        content_types = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                         '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
                         '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
                         '  <Default Extension="xml" ContentType="application/xml"/>',
                         '  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
                         '  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>']
        for idx in range(1, len(sheets) + 1):
            content_types.append(f'  <Override PartName="/xl/worksheets/sheet{idx}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
        content_types.append('</Types>')
        z.writestr('[Content_Types].xml', '\n'.join(content_types))
        
        z.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>''')

        wb_rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
        for idx in range(1, len(sheets) + 1):
            wb_rels.append(f'  <Relationship Id="rId{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{idx}.xml"/>')
        wb_rels.append(f'  <Relationship Id="rId{len(sheets)+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>')
        wb_rels.append('</Relationships>')
        z.writestr('xl/_rels/workbook.xml.rels', '\n'.join(wb_rels))

        wb_xml = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                  '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
                  '  <sheets>']
        for idx, (name, _, _) in enumerate(sheets, 1):
            wb_xml.append(f'    <sheet name="{escape_xml(name)}" sheetId="{idx}" r:id="rId{idx}"/>')
        wb_xml.append('  </sheets>')
        wb_xml.append('</workbook>')
        z.writestr('xl/workbook.xml', '\n'.join(wb_xml))

        styles_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="11"/><name val="Segoe UI"/></font>
    <font><b/><sz val="11"/><name val="Segoe UI"/><color rgb="FFFFFFFF"/></font>
  </fonts>
  <fills count="3">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF1E293B"/></patternFill></fill>
  </fills>
  <borders count="1"><border><left/><right/><top/><bottom/></border></borders>
  <cellXfs count="2">
    <xf fontId="0" fillId="0" borderId="0"/>
    <xf fontId="1" fillId="2" borderId="0" applyFont="1" applyFill="1"/>
  </cellXfs>
</styleSheet>'''
        z.writestr('xl/styles.xml', styles_xml)

        for idx, (_, headers, rows) in enumerate(sheets, 1):
            z.writestr(f'xl/worksheets/sheet{idx}.xml', build_sheet_xml(headers, rows))

    return buf.getvalue()

def sync_excel_files():
    """توليد ومزامنة ملف الإكسيل و CSV لحظياً مع كل تسجيل جديد أو حجز على المنصة"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. جلب بيانات المستخدمين والعملاء المسجلين
        cursor.execute('SELECT * FROM users ORDER BY id DESC')
        user_rows = cursor.fetchall()

        user_headers = [
            'مُعرّف الحساب (ID)',
            'الاسم بالكامل',
            'الاسم الأول',
            'الاسم الأخير',
            'رقم الهاتف المحمول',
            'البريد الإلكتروني (جيميل)',
            'العنوان ومحل الإقامة',
            'نوع الحساب والصفة',
            'رقم رخصة القيادة',
            'رقم الحافلة المخصصة',
            'تاريخ وتوقيت التسجيل'
        ]

        roles_ar = {
            'customer': 'عميل مسافر',
            'driver': 'سائق حافلة',
            'admin': 'مدير المحطة'
        }

        user_data = []
        for u in user_rows:
            user_data.append([
                u['id'],
                u['name'] or f"{u['first_name']} {u['last_name']}",
                u['first_name'] or '',
                u['last_name'] or '',
                u['phone'] or '',
                u['email'] or '',
                u['address'] or '',
                roles_ar.get(u['role'], u['role'] or ''),
                u['license_number'] or '---',
                u['bus_number'] or '---',
                u['created_at'] or ''
            ])

        # 2. جلب سجل الحجوزات والتذاكر
        cursor.execute('''
            SELECT b.*, t.from_city, t.to_city, t.departure_time_label, t.trip_date, t.bus_number
            FROM bookings b
            LEFT JOIN trips t ON b.trip_id = t.id
            ORDER BY b.booking_date DESC
        ''')
        booking_rows = cursor.fetchall()

        booking_headers = [
            'رقم الحجز (PNR)',
            'اسم العميل المسافر',
            'رقم الهاتف',
            'الرقم القومي',
            'خط السير (من - إلى)',
            'موعد وتاريخ الرحلة',
            'رقم الحافلة',
            'المقاعد المحجوزة',
            'إجمالي المبلغ المستحق',
            'طريقة السداد',
            'حالة الدفع',
            'صعود الحافلة',
            'تاريخ وتوقيت الحجز'
        ]

        pay_methods = {'card': 'بطاقة بنكية / فيزا', 'wallet': 'محفظة ذكية (فودافون كاش)', 'cash': 'سداد نقدي بالمحطة'}
        pay_status = {'paid': 'مدفوعة بالكامل', 'pending_cash': 'حجز مبدئي - دفع بالمحطة'}

        booking_data = []
        for b in booking_rows:
            seats_str = ''
            try:
                seats_list = json.loads(b['seats'])
                seats_str = ' ، '.join(map(str, seats_list))
            except:
                seats_str = str(b['seats'] or '')

            route = f"{b['from_city'] or ''} ⬅️ {b['to_city'] or ''}" if b['from_city'] else b['trip_id']
            time_date = f"{b['trip_date'] or ''} ({b['departure_time_label'] or ''})"
            boarded_status = 'تم الصعود ✅' if b['boarded'] == 1 else 'في انتظار الصعود ⏳'

            booking_data.append([
                b['pnr'],
                b['customer_name'] or '',
                b['customer_phone'] or '',
                b['national_id'] or '',
                route,
                time_date,
                b['bus_number'] or '---',
                seats_str,
                f"{b['total_amount']} ج.م",
                pay_methods.get(b['payment_method'], b['payment_method']),
                pay_status.get(b['payment_status'], b['payment_status']),
                boarded_status,
                b['booking_date'] or ''
            ])

        conn.close()

        # كتابة ملف XLSX متكامل ومتعدد الصفحات
        sheets = [
            ('المستخدمين المسجلين', user_headers, user_data),
            ('سجل الحجوزات والتذاكر', booking_headers, booking_data)
        ]
        xlsx_bytes = generate_excel_bytes(sheets)
        with open(EXCEL_FILE, 'wb') as f:
            f.write(xlsx_bytes)

        # كتابة ملف CSV مع BOM UTF-8 لفتح الحروف العربية بشكل تلقائي وسلس في إكسيل
        with open(CSV_FILE, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(user_headers)
            writer.writerows(user_data)

        print(f"📊 [Excel Sync] تم تحديث ملف الإكسيل بنجاح ({len(user_data)} مستخدم، {len(booking_data)} حجز) في: {EXCEL_FILE}")
    except Exception as e:
        print(f"⚠️ خطأ أثناء تحديث ملف الإكسيل: {e}")


# ==================== 2. معالج الطلبات (HTTP API Handler) ====================
class BusStationAPIHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def send_json(self, data, status_code=200):
        response_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def get_parsed_url(self):
        return urllib.parse.urlparse(self.path)

    def get_query_params(self):
        parsed = self.get_parsed_url()
        return urllib.parse.parse_qs(parsed.query)

    def get_request_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            raw_body = self.rfile.read(content_length).decode('utf-8')
            try:
                return json.loads(raw_body)
            except json.JSONDecodeError:
                return {}
        return {}

    # ----------------- طلبات GET -----------------
    def do_GET(self):
        parsed = self.get_parsed_url()
        path = parsed.path

        if path.startswith('/api/'):
            try:
                # 1. قائمة الرحلات (مع دعم الفلترة)
                if path == '/api/trips':
                    self.handle_get_trips()
                # 2. تفاصيل رحلة محددة
                elif path.startswith('/api/trips/'):
                    trip_id = path.replace('/api/trips/', '').strip('/')
                    self.handle_get_trip_detail(trip_id)
                # 3. قائمة الحجوزات
                elif path == '/api/bookings':
                    self.handle_get_bookings()
                # 4. قائمة السائقين
                elif path == '/api/drivers':
                    self.handle_get_drivers()
                # 5. إحصائيات الإدارة
                elif path == '/api/admin/stats':
                    self.handle_get_stats()
                # 6. رحلات السائق الحالي
                elif path == '/api/driver/manifest':
                    self.handle_get_driver_manifest()
                # 7. تصدير ملف الإكسيل المباشر المربوط بالمنصة
                elif path == '/api/export/excel':
                    self.handle_export_excel()
                elif path == '/api/export/csv':
                    self.handle_export_csv()
                elif path == '/api/export/status':
                    self.handle_export_status()
                else:
                    self.send_json({'error': 'نقطة النهاية غير موجودة'}, 404)
            except Exception as e:
                self.send_json({'error': str(e)}, 500)
            return

        # تقديم ملفات الفرونت إند (HTML, CSS, JS) تلقائياً
        super().do_GET()

    # ----------------- طلبات POST -----------------
    def do_POST(self):
        parsed = self.get_parsed_url()
        path = parsed.path

        if path.startswith('/api/'):
            try:
                body = self.get_request_body()

                # 1. تسجيل مستخدم جديد
                if path == '/api/auth/register':
                    self.handle_register(body)
                # 2. تسجيل الدخول
                elif path == '/api/auth/login':
                    self.handle_login(body)
                # 3. إنشاء حجز جديد وسداد الأجرة
                elif path == '/api/bookings':
                    self.handle_create_booking(body)
                # 4. جدولة رحلة جديدة (للإدارة)
                elif path == '/api/trips':
                    self.handle_create_trip(body)
                # 5. تأكيد صعود الراكب (للسائق)
                elif path == '/api/driver/checkin':
                    self.handle_passenger_checkin(body)
                # 6. تحديث حالة الرحلة (للسائق)
                elif path == '/api/driver/trip-status':
                    self.handle_update_trip_status(body)
                else:
                    self.send_json({'error': 'نقطة النهاية غير موجودة'}, 404)
            except Exception as e:
                self.send_json({'error': str(e)}, 500)
            return

        self.send_json({'error': 'طريقة غير مدعومة'}, 405)

    # ----------------- طلبات DELETE -----------------
    def do_DELETE(self):
        parsed = self.get_parsed_url()
        path = parsed.path

        if path.startswith('/api/trips/'):
            trip_id = path.replace('/api/trips/', '').strip('/')
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM trips WHERE id = ?', (trip_id,))
            conn.commit()
            conn.close()
            self.send_json({'success': True, 'message': f'تم حذف الرحلة {trip_id} بنجاح'})
            return

        self.send_json({'error': 'طريقة غير مدعومة'}, 405)

    # ==================== 3. معالجات العمليات (Controllers) ====================

    def handle_register(self, body):
        first_name = normalize_input(body.get('first_name', '')).strip()
        last_name = normalize_input(body.get('last_name', '')).strip()
        phone = normalize_phone(body.get('phone', ''))
        raw_phone = normalize_input(body.get('phone', '')).strip()
        email = normalize_input(body.get('email', '')).lower().strip()
        address = normalize_input(body.get('address', '')).strip()
        password = body.get('password', '').strip()
        role = body.get('role', 'customer').strip()
        license_number = normalize_input(body.get('license_number', '')).strip()
        bus_number = normalize_input(body.get('bus_number', '')).strip()
        admin_code = body.get('admin_security_code', '').strip()

        if not first_name or not last_name or not phone or not email or not address or not password:
            self.send_json({'error': 'يرجى استكمال جميع البيانات الأساسية: الاسم الأول، الأخير، رقم الهاتف، الجيميل، العنوان، وكلمة المرور'}, 400)
            return

        # 🔒 فحص أمان صارم: منع أي شخص من إنشاء حساب إدارة بدون كود التفويض السري
        if role == 'admin':
            if admin_code != ADMIN_SECURITY_PASSCODE:
                self.send_json({
                    'error': '⛔ تم رفض الطلب: كود تفويض إدارة المحطة غير صحيح! لا يمكن لأي شخص إنشاء حساب إدارة دون إذن رسمي.'
                }, 403)
                return

        full_name = f"{first_name} {last_name}".strip()

        conn = get_db_connection()
        cursor = conn.cursor()

        # فحص عدم تكرار البريد أو الهاتف (بشكل غير حساس لحالة الأحرف)
        cursor.execute('''
        SELECT id FROM users 
        WHERE LOWER(TRIM(email)) = LOWER(?) OR TRIM(phone) = ? OR TRIM(phone) = ?
        ''', (email, phone, raw_phone))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            self.send_json({'error': 'عذراً، هذا البريد الإلكتروني أو رقم الهاتف مسجل بالفعل مسبقاً! يمكنك تسجيل الدخول مباشرة.'}, 409)
            return

        cursor.execute('''
        INSERT INTO users (first_name, last_name, name, email, phone, address, password, role, license_number, bus_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (first_name, last_name, full_name, email, phone, address, password, role, license_number, bus_number))
        user_id = cursor.lastrowid

        # إذا كان الحساب لسائق، نضيفه لأسطول سائقي المحطة
        if role == 'driver':
            drv_id = f"DRV-{user_id + 100}"
            bus_info = bus_number if bus_number else "أتوبيس معتمد بالمحطة"
            cursor.execute('''
            INSERT OR REPLACE INTO drivers (id, name, phone, bus_info, rating, is_active)
            VALUES (?, ?, ?, ?, 5.0, 1)
            ''', (drv_id, full_name, phone, bus_info))

        conn.commit()
        conn.close()

        # مزامنة وتحديث ملف الإكسيل فوراً بالبيانات الجديدة
        sync_excel_files()

        user_data = {
            'id': user_id,
            'first_name': first_name,
            'last_name': last_name,
            'name': full_name,
            'email': email,
            'phone': phone,
            'address': address,
            'role': role,
            'bus_number': bus_number,
            'license_number': license_number
        }

        self.send_json({
            'success': True,
            'message': f'🎉 أهلاً بك يا {first_name}! تم إنشاء حسابك وحفظ بياناتك وتحديث ملف الإكسيل المربوط بالمنصة.',
            'user': user_data
        })

    def handle_login(self, body):
        role = body.get('role', None)
        raw_identifier = body.get('identifier', '')
        password = body.get('password', '')

        identifier = normalize_input(raw_identifier).strip()
        phone_norm = normalize_phone(raw_identifier)

        if not identifier or not password:
            self.send_json({'error': 'يرجى إدخال البريد الإلكتروني أو رقم الهاتف وكلمة المرور'}, 400)
            return

        conn = get_db_connection()
        cursor = conn.cursor()

        # البحث المرن والذكي عن المستخدم (بالبريد الإلكتروني غير الحساس للأحرف، أو برقم الهاتف، أو بالاسم)
        cursor.execute('''
        SELECT id, first_name, last_name, name, email, phone, address, role, license_number, bus_number, password
        FROM users 
        WHERE (
            LOWER(TRIM(email)) = LOWER(?) 
            OR TRIM(phone) = ? 
            OR TRIM(phone) = ?
            OR LOWER(TRIM(name)) = LOWER(?)
            OR LOWER(TRIM(first_name)) = LOWER(?)
        )
        LIMIT 1
        ''', (identifier, identifier, phone_norm, identifier, identifier))

        user = cursor.fetchone()
        conn.close()

        if user:
            # التحقق من كلمة المرور
            db_password = user['password']
            if db_password == password or db_password == password.strip():
                user_data = dict(user)
                user_data.pop('password', None)
                self.send_json({
                    'success': True,
                    'message': f'مرحباً بك مجدداً {user_data.get("name")}',
                    'user': user_data
                })
                return
            else:
                self.send_json({'error': 'كلمة المرور غير صحيحة! يرجى التأكد من كتابة كلمة المرور بدقة.'}, 401)
                return
        else:
            self.send_json({'error': 'لم يتم العثور على حساب بهذا البريد أو الهاتف! يرجى التأكد من كتابة البريد أو الهاتف المسجل أو إنشاء حساب جديد.'}, 401)
            return

    def handle_get_trips(self):
        params = self.get_query_params()
        from_city = params.get('from', [None])[0]
        to_city = params.get('to', [None])[0]

        conn = get_db_connection()
        cursor = conn.cursor()

        query = 'SELECT * FROM trips WHERE 1=1'
        args = []
        if from_city:
            query += ' AND from_city = ?'
            args.append(from_city)
        if to_city:
            query += ' AND to_city = ?'
            args.append(to_city)

        query += ' ORDER BY departure_time ASC'
        cursor.execute(query, args)
        rows = cursor.fetchall()

        trips_list = []
        for r in rows:
            trip_dict = dict(r)
            # جلب المقاعد المحجوزة لهذه الرحلة
            cursor.execute('SELECT seats FROM bookings WHERE trip_id = ?', (trip_dict['id'],))
            booking_rows = cursor.fetchall()
            booked_seats = []
            for b in booking_rows:
                try:
                    s_list = json.loads(b['seats'])
                    booked_seats.extend(s_list)
                except:
                    pass
            trip_dict['booked_seats'] = booked_seats
            trips_list.append(trip_dict)

        conn.close()
        self.send_json({'success': True, 'trips': trips_list})

    def handle_get_trip_detail(self, trip_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM trips WHERE id = ?', (trip_id,))
        trip = cursor.fetchone()

        if not trip:
            conn.close()
            self.send_json({'error': 'الرحلة غير موجودة'}, 404)
            return

        trip_dict = dict(trip)
        cursor.execute('SELECT seats FROM bookings WHERE trip_id = ?', (trip_id,))
        booking_rows = cursor.fetchall()
        booked_seats = []
        for b in booking_rows:
            try:
                booked_seats.extend(json.loads(b['seats']))
            except:
                pass

        trip_dict['booked_seats'] = booked_seats
        conn.close()
        self.send_json({'success': True, 'trip': trip_dict})

    def handle_create_booking(self, body):
        trip_id = body.get('trip_id')
        name = body.get('customer_name')
        phone = body.get('customer_phone')
        nat_id = body.get('national_id', '---')
        seats = body.get('seats', [])
        payment_method = body.get('payment_method', 'card')

        if not trip_id or not name or not phone or not seats:
            self.send_json({'error': 'بيانات الحجز غير مكتملة'}, 400)
            return

        conn = get_db_connection()
        cursor = conn.cursor()

        # التأكد من الرحلة وسعرها
        cursor.execute('SELECT price, from_city, to_city, departure_time_label, trip_date, bus_number, bus_class_label FROM trips WHERE id = ?', (trip_id,))
        trip = cursor.fetchone()
        if not trip:
            conn.close()
            self.send_json({'error': 'الرحلة المحددة غير موجودة'}, 404)
            return

        # فحص المقاعد هل تم حجز أي منها بالفعل
        cursor.execute('SELECT seats FROM bookings WHERE trip_id = ?', (trip_id,))
        existing_bookings = cursor.fetchall()
        already_booked = set()
        for eb in existing_bookings:
            try:
                already_booked.update(json.loads(eb['seats']))
            except:
                pass

        for s in seats:
            if s in already_booked:
                conn.close()
                self.send_json({'error': f'المقعد رقم {s} تم حجزه بالفعل! يرجى اختيار مقعد آخر'}, 409)
                return

        # توليد كود PNR مميز
        pnr = f"EXP-{int(datetime.now().timestamp() % 100000):05d}"
        total_amount = len(seats) * trip['price']
        payment_status = 'pending_cash' if payment_method == 'cash' else 'paid'

        cursor.execute('''
        INSERT INTO bookings (pnr, trip_id, customer_name, customer_phone, national_id, seats, total_amount, payment_method, payment_status, boarded)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        ''', (pnr, trip_id, name, phone, nat_id, json.dumps(seats), total_amount, payment_method, payment_status))

        conn.commit()
        conn.close()

        # مزامنة وتحديث ملف الإكسيل فوراً بالبيانات الجديدة
        sync_excel_files()

        # بيانات التذكرة الصادرة
        ticket_data = {
            'pnr': pnr,
            'trip_id': trip_id,
            'from_city': trip['from_city'],
            'to_city': trip['to_city'],
            'departure_time': trip['departure_time_label'],
            'trip_date': trip['trip_date'],
            'bus_number': trip['bus_number'],
            'bus_class': trip['bus_class_label'],
            'customer_name': name,
            'customer_phone': phone,
            'seats': seats,
            'total_amount': total_amount,
            'payment_method': payment_method,
            'payment_status': payment_status,
            'qr_payload': f"BUS-STATION|{pnr}|{trip_id}|SEATS:{','.join(map(str, seats))}|PAID:{total_amount}"
        }

        self.send_json({'success': True, 'message': 'تم تسجيل الحجز وسداد الأجرة بنجاح!', 'ticket': ticket_data})

    def handle_get_bookings(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT b.*, t.from_city, t.to_city, t.departure_time_label, t.trip_date
        FROM bookings b
        JOIN trips t ON b.trip_id = t.id
        ORDER BY b.booking_date DESC
        ''')
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d['seats'] = json.loads(d['seats'])
            except:
                pass
            result.append(d)
        conn.close()
        self.send_json({'success': True, 'bookings': result})

    def handle_get_drivers(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM drivers WHERE is_active = 1')
        drivers = [dict(d) for d in cursor.fetchall()]
        conn.close()
        self.send_json({'success': True, 'drivers': drivers})

    def handle_create_trip(self, body):
        conn = get_db_connection()
        cursor = conn.cursor()

        new_id = f"EX-{int(datetime.now().timestamp() % 1000):03d}"
        class_map = {'VIP': 'VIP فاخر', 'Business': 'رجال أعمال', 'Standard': 'اقتصادي مريح'}
        b_class = body.get('bus_class', 'VIP')

        cursor.execute('''
        INSERT INTO trips (id, from_city, from_station, to_city, to_station, departure_time, departure_time_label,
                          arrival_time_label, duration, trip_date, price, bus_class, bus_class_label, bus_number, driver_name, total_seats, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 28, 'ready')
        ''', (
            new_id,
            body.get('from_city'),
            f"موقف {body.get('from_city')} المركزي",
            body.get('to_city'),
            f"موقف {body.get('to_city')}",
            body.get('departure_time'),
            body.get('departure_time'),
            'بعد 4 ساعات',
            '4 ساعات تقريباً',
            body.get('trip_date'),
            body.get('price', 150),
            b_class,
            class_map.get(b_class, b_class),
            body.get('bus_number', 'أتوبيس حديث'),
            body.get('driver_name', 'كابتن معتمد')
        ))

        conn.commit()
        conn.close()

        # مزامنة وتحديث ملف الإكسيل فوراً بالبيانات الجديدة
        sync_excel_files()
        self.send_json({'success': True, 'trip_id': new_id, 'message': 'تمت إضافة الرحلة للجدول بنجاح'})

    def handle_passenger_checkin(self, body):
        pnr = body.get('pnr')
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT boarded FROM bookings WHERE pnr = ?', (pnr,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            self.send_json({'error': 'كود الحجز غير موجود'}, 404)
            return

        new_boarded = 0 if row['boarded'] == 1 else 1
        cursor.execute('UPDATE bookings SET boarded = ? WHERE pnr = ?', (new_boarded, pnr))
        conn.commit()
        conn.close()

        # مزامنة وتحديث ملف الإكسيل فوراً بالبيانات الجديدة
        sync_excel_files()
        self.send_json({'success': True, 'boarded': new_boarded})

    def handle_update_trip_status(self, body):
        trip_id = body.get('trip_id')
        status = body.get('status')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE trips SET status = ? WHERE id = ?', (status, trip_id))
        conn.commit()
        conn.close()

        # مزامنة وتحديث ملف الإكسيل فوراً بالبيانات الجديدة
        sync_excel_files()
        self.send_json({'success': True, 'status': status})

    def handle_get_driver_manifest(self):
        params = self.get_query_params()
        driver_name = params.get('driver_name', ['محمود'])[0]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM trips WHERE driver_name LIKE ? ORDER BY departure_time ASC LIMIT 1', (f"%{driver_name}%",))
        trip = cursor.fetchone()

        if not trip:
            cursor.execute('SELECT * FROM trips ORDER BY departure_time ASC LIMIT 1')
            trip = cursor.fetchone()

        trip_dict = dict(trip) if trip else None
        passengers = []
        if trip_dict:
            cursor.execute('SELECT * FROM bookings WHERE trip_id = ? ORDER BY booking_date DESC', (trip_dict['id'],))
            p_rows = cursor.fetchall()
            for p in p_rows:
                pd = dict(p)
                try:
                    pd['seats'] = json.loads(pd['seats'])
                except:
                    pass
                passengers.append(pd)

        conn.close()
        self.send_json({'success': True, 'trip': trip_dict, 'passengers': passengers})

    def handle_get_stats(self):
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COALESCE(SUM(total_amount), 0) FROM bookings WHERE payment_status = 'paid'")
        total_revenue = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM bookings")
        total_bookings = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM trips")
        total_trips = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM drivers WHERE is_active = 1")
        total_drivers = cursor.fetchone()[0]

        conn.close()
        self.send_json({
            'success': True,
            'stats': {
                'total_revenue': total_revenue,
                'total_bookings': total_bookings,
                'total_trips': total_trips,
                'total_drivers': total_drivers
            }
        })

    # ----------------- خدمات تصدير وتحميل الإكسيل المباشر -----------------
    def handle_export_excel(self):
        sync_excel_files()
        if not os.path.exists(EXCEL_FILE):
            self.send_json({'error': 'ملف الإكسيل غير متوفر حالياً'}, 404)
            return

        with open(EXCEL_FILE, 'rb') as f:
            data = f.read()

        self.send_response(200)
        self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.send_header('Content-Disposition', 'attachment; filename="registered_users.xlsx"')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)

    def handle_export_csv(self):
        sync_excel_files()
        if not os.path.exists(CSV_FILE):
            self.send_json({'error': 'ملف CSV غير متوفر حالياً'}, 404)
            return

        with open(CSV_FILE, 'rb') as f:
            data = f.read()

        self.send_response(200)
        self.send_header('Content-Type', 'text/csv; charset=utf-8-sig')
        self.send_header('Content-Disposition', 'attachment; filename="registered_users.csv"')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)

    def handle_export_status(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        users_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM bookings')
        bookings_count = cursor.fetchone()[0]
        conn.close()

        self.send_json({
            'success': True,
            'users_count': users_count,
            'bookings_count': bookings_count,
            'excel_file_path': EXCEL_FILE,
            'csv_file_path': CSV_FILE,
            'excel_file_size': os.path.getsize(EXCEL_FILE) if os.path.exists(EXCEL_FILE) else 0,
            'last_sync': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })




# ==================== 4. تشغيل الخادم ====================
def run_server():
    init_db()
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, BusStationAPIHandler)
    print("=" * 60)
    print(f" 🚀 خادم الباك إند لمحطة الأتوبيس يعمل الآن على: http://localhost:{PORT}")
    print(f" 📂 المجلد الثابت: {STATIC_DIR}")
    print(f" 🗄️ قاعدة البيانات: {DB_FILE}")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف الخادم.")
        httpd.server_close()

if __name__ == '__main__':
    run_server()
