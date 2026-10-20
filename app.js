/**
 * محطة إكسبريس للنقل البري والحافلات
 * ملف المنطق البرمجي والربط مع الباك إند (Frontend - Backend Integration)
 * يدعم العمل المباشر مع API السيرفر (Python/SQLite) مع دعم العمل المحلي التلقائي.
 */

const API_BASE = '/api';

const DEFAULT_DRIVERS = [
    { id: 'DRV-101', name: 'محمود حسن السعيد', phone: '01099887766', bus: 'أتوبيس 705 (مرسيدس سوبر جيت)', rating: 4.9, active: true },
    { id: 'DRV-102', name: 'إبراهيم كمال الدين', phone: '01122334455', bus: 'أتوبيس 910 (مان ترانس)', rating: 4.8, active: true },
    { id: 'DRV-103', name: 'خالد عبد العزيز', phone: '01233445566', bus: 'أتوبيس 302 (دايو كلاسيك)', rating: 4.7, active: true },
    { id: 'DRV-104', name: 'سامح فاروق الشريف', phone: '01555667788', bus: 'أتوبيس 441 (مرسيدس توريزمو)', rating: 4.9, active: true }
];

const DEFAULT_TRIPS = [
    {
        id: 'EX-804',
        from: 'القاهرة',
        fromStation: 'موقف رمسيس / الترجمان',
        to: 'الإسكندرية',
        toStation: 'موقف محرم بك',
        departureTime: '14:30',
        departureTimeLabel: '02:30 م',
        arrivalTimeLabel: '05:30 م',
        duration: '3 ساعات',
        date: new Date().toISOString().split('T')[0],
        price: 180,
        busClass: 'VIP',
        busClassLabel: 'VIP فاخر',
        busNumber: 'أتوبيس 705 (مرسيدس سوبر جيت)',
        driverName: 'محمود حسن السعيد',
        totalSeats: 28,
        bookedSeats: [1, 2, 7, 8, 15],
        status: 'ready'
    },
    {
        id: 'EX-805',
        from: 'القاهرة',
        fromStation: 'موقف رمسيس',
        to: 'شرم الشيخ',
        toStation: 'موقف الرويسات',
        departureTime: '07:00',
        departureTimeLabel: '07:00 ص',
        arrivalTimeLabel: '01:30 م',
        duration: '6.5 ساعات',
        date: new Date().toISOString().split('T')[0],
        price: 320,
        busClass: 'VIP',
        busClassLabel: 'VIP فاخر',
        busNumber: 'أتوبيس 910 (مان ترانس)',
        driverName: 'إبراهيم كمال الدين',
        totalSeats: 28,
        bookedSeats: [3, 4, 11, 12, 19, 20],
        status: 'ready'
    },
    {
        id: 'EX-806',
        from: 'الإسكندرية',
        fromStation: 'موقف محرم بك',
        to: 'المنصورة',
        toStation: 'المحطة المركزية',
        departureTime: '10:00',
        departureTimeLabel: '10:00 ص',
        arrivalTimeLabel: '01:00 م',
        duration: '3 ساعات',
        date: new Date().toISOString().split('T')[0],
        price: 120,
        busClass: 'Standard',
        busClassLabel: 'اقتصادي مريح',
        busNumber: 'أتوبيس 302 (دايو كلاسيك)',
        driverName: 'خالد عبد العزيز',
        totalSeats: 28,
        bookedSeats: [5, 6, 9],
        status: 'ready'
    },
    {
        id: 'EX-807',
        from: 'القاهرة',
        fromStation: 'موقف رمسيس',
        to: 'الغردقة',
        toStation: 'محطة الدهار',
        departureTime: '23:30',
        departureTimeLabel: '11:30 م',
        arrivalTimeLabel: '05:30 ص',
        duration: '6 ساعات',
        date: new Date().toISOString().split('T')[0],
        price: 290,
        busClass: 'Business',
        busClassLabel: 'رجال أعمال',
        busNumber: 'أتوبيس 441 (مرسيدس توريزمو)',
        driverName: 'سامح فاروق الشريف',
        totalSeats: 28,
        bookedSeats: [10, 14, 18, 22],
        status: 'ready'
    },
    {
        id: 'EX-808',
        from: 'القاهرة',
        fromStation: 'موقف رمسيس',
        to: 'أسوان',
        toStation: 'موقف الأقاليم',
        departureTime: '18:00',
        departureTimeLabel: '06:00 م',
        arrivalTimeLabel: '07:00 ص',
        duration: '13 ساعة',
        date: new Date().toISOString().split('T')[0],
        price: 450,
        busClass: 'VIP',
        busClassLabel: 'VIP فاخر',
        busNumber: 'أتوبيس 705 (مرسيدس سوبر جيت)',
        driverName: 'محمود حسن السعيد',
        totalSeats: 28,
        bookedSeats: [2, 3, 4, 16],
        status: 'ready'
    }
];

const DEFAULT_BOOKINGS = [];

class BusStationApp {
    constructor() {
        this.trips = [];
        this.bookings = [];
        this.drivers = [];
        this.currentUser = null;
        this.selectedTrip = null;
        this.selectedSeats = [];
        this.currentFilter = 'all';
        this.isBackendConnected = false;
    }

    async init() {
        await this.loadInitialData();
        this.setupNavigation();
        this.setupEventListeners();
        this.renderTrips();
        this.renderCustomerBookings();
        this.renderDriverPortal();
        this.renderAdminDashboard();
        this.updateUserUI();

        const searchDateInput = document.getElementById('search-date');
        if (searchDateInput) searchDateInput.value = new Date().toISOString().split('T')[0];
        const newTripDate = document.getElementById('new-trip-date');
        if (newTripDate) newTripDate.value = new Date().toISOString().split('T')[0];
    }

    // ==================== طبقة الربط مع الباك إند (API Client) ====================
    async apiRequest(endpoint, method = 'GET', data = null) {
        try {
            const options = {
                method: method,
                headers: { 'Content-Type': 'application/json' }
            };
            if (data && (method === 'POST' || method === 'PUT')) {
                options.body = JSON.stringify(data);
            }
            const res = await fetch(`${API_BASE}${endpoint}`, options);
            const resData = await res.json().catch(() => null);
            if (!res.ok) {
                const errorMsg = (resData && resData.error) ? resData.error : `خطأ في الخادم (${res.status})`;
                return { success: false, error: errorMsg };
            }
            return resData;
        } catch (err) {
            console.warn(`[API] فشل الاتصال بنقطة ${endpoint}:`, err.message);
            return { success: false, error: 'فشل الاتصال بالخادم. يرجى التأكد من تشغيل الخادم.', networkError: true };
        }
    }

    async loadInitialData() {
        // فحص الاتصال بالباك إند
        const apiTrips = await this.apiRequest('/trips');
        if (apiTrips && apiTrips.success) {
            this.isBackendConnected = true;
            this.trips = apiTrips.trips.map(t => this.mapApiTrip(t));

            const apiBookings = await this.apiRequest('/bookings');
            if (apiBookings && apiBookings.success) {
                this.bookings = apiBookings.bookings.map(b => this.mapApiBooking(b));
            }

            const apiDrivers = await this.apiRequest('/drivers');
            if (apiDrivers && apiDrivers.success) {
                this.drivers = apiDrivers.drivers;
            }

            this.notify('🟢 تم الاتصال بنجاح بخادم الباك إند وقاعدة بيانات SQLite!', 'success');
        } else {
            // الرجوع للبيانات المخزنة محلياً عند عدم توفر الخادم
            this.isBackendConnected = false;
            const storedTrips = localStorage.getItem('bus_station_trips');
            const storedBookings = localStorage.getItem('bus_station_bookings');
            this.trips = storedTrips ? JSON.parse(storedTrips) : DEFAULT_TRIPS;
            this.bookings = storedBookings ? JSON.parse(storedBookings) : DEFAULT_BOOKINGS;
            this.drivers = DEFAULT_DRIVERS;
        }

        const storedUser = localStorage.getItem('bus_station_current_user');
        if (storedUser) {
            try {
                const u = JSON.parse(storedUser);
                if (u.email === 'ahmed@example.com' || u.email === 'mahmoud@driver.com' || u.email === 'admin@station.com') {
                    localStorage.removeItem('bus_station_current_user');
                    this.currentUser = null;
                } else {
                    this.currentUser = u;
                }
            } catch (err) {
                this.currentUser = null;
            }
        } else {
            this.currentUser = null;
        }
    }

    mapApiTrip(t) {
        return {
            id: t.id,
            from: t.from_city,
            fromStation: t.from_station,
            to: t.to_city,
            toStation: t.to_station,
            departureTime: t.departure_time,
            departureTimeLabel: t.departure_time_label,
            arrivalTimeLabel: t.arrival_time_label,
            duration: t.duration,
            date: t.trip_date,
            price: t.price,
            busClass: t.bus_class,
            busClassLabel: t.bus_class_label,
            busNumber: t.bus_number,
            driverName: t.driver_name,
            totalSeats: t.total_seats || 28,
            bookedSeats: t.booked_seats || [],
            status: t.status || 'ready'
        };
    }

    mapApiBooking(b) {
        return {
            pnr: b.pnr,
            tripId: b.trip_id,
            customerName: b.customer_name,
            customerPhone: b.customer_phone,
            nationalId: b.national_id,
            seats: Array.isArray(b.seats) ? b.seats : [],
            totalAmount: b.total_amount,
            paymentMethod: b.payment_method,
            paymentStatus: b.payment_status,
            bookingDate: b.booking_date,
            boarded: b.boarded === 1,
            from_city: b.from_city,
            to_city: b.to_city,
            route: `${b.from_city || ''} ⬅️ ${b.to_city || ''}`,
            departureTimeLabel: b.departure_time_label || ''
        };
    }

    saveLocalState() {
        if (!this.isBackendConnected) {
            localStorage.setItem('bus_station_trips', JSON.stringify(this.trips));
            localStorage.setItem('bus_station_bookings', JSON.stringify(this.bookings));
        }
        localStorage.setItem('bus_station_current_user', JSON.stringify(this.currentUser));
    }

    // ==================== التنقل وتسجيل الدخول ====================
    setupNavigation() {
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.switchView(btn.getAttribute('data-target'));
            });
        });

        document.getElementById('btn-open-login').addEventListener('click', () => {
            this.selectLoginRole('customer');
            this.switchAuthMode('login');
            this.openModal('login-modal');
        });
        document.getElementById('btn-logout').addEventListener('click', () => {
            this.currentUser = null;
            this.saveLocalState();
            this.updateUserUI();
            this.switchView('customer-view');
            this.notify('تم تسجيل الخروج', 'info');
        });
    }

    switchView(viewId) {
        if (viewId === 'admin-view' && (!this.currentUser || this.currentUser.role !== 'admin')) {
            this.notify('يجب تسجيل الدخول كمسؤول إدارة للوصول إلى لوحة التحكم', 'error');
            this.selectLoginRole('admin');
            this.openModal('login-modal');
            return;
        }

        if (viewId === 'driver-view' && (!this.currentUser || this.currentUser.role !== 'driver')) {
            this.notify('يجب تسجيل الدخول كسائق للوصول إلى بوابة الكابتن', 'error');
            this.selectLoginRole('driver');
            this.openModal('login-modal');
            return;
        }

        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        const activeNavBtn = document.querySelector(`.nav-btn[data-target="${viewId}"]`);
        if (activeNavBtn) activeNavBtn.classList.add('active');

        document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));
        const targetSection = document.getElementById(viewId);
        if (targetSection) {
            targetSection.classList.add('active');
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        if (viewId === 'driver-view') this.renderDriverPortal();
        if (viewId === 'admin-view') this.renderAdminDashboard();
        if (viewId === 'customer-view') this.renderCustomerBookings();
    }

    updateUserUI() {
        const badge = document.getElementById('user-badge');
        const loginBtn = document.getElementById('btn-open-login');
        const userNameSpan = document.getElementById('user-display-name');
        const userRoleSmall = document.getElementById('user-display-role');
        const userInitials = document.getElementById('user-avatar-initials');

        if (this.currentUser) {
            badge.style.display = 'flex';
            loginBtn.style.display = 'none';
            userNameSpan.textContent = this.currentUser.name;
            const rolesMap = { customer: 'عميل مسافر', driver: 'سائق حافلة', admin: 'مدير المحطة' };
            userRoleSmall.textContent = rolesMap[this.currentUser.role] || this.currentUser.role;
            userInitials.textContent = this.currentUser.name.charAt(0);
        } else {
            badge.style.display = 'none';
            loginBtn.style.display = 'flex';
        }
    }

    selectLoginRole(role) {
        document.querySelectorAll('.role-btn').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-role') === role);
        });

        const label = document.getElementById('login-identifier-label');
        const input = document.getElementById('login-identifier');
        const pwd = document.getElementById('login-password');

        if (role === 'customer') {
            label.innerHTML = '<i class="fa-solid fa-envelope"></i> البريد الإلكتروني أو رقم الهاتف للعميل';
            input.placeholder = 'name@gmail.com أو 010XXXXXXXX';
        } else if (role === 'driver') {
            label.innerHTML = '<i class="fa-solid fa-id-card"></i> كود السائق أو رقم الهاتف';
            input.placeholder = 'driver@gmail.com أو 010XXXXXXXX';
        } else {
            label.innerHTML = '<i class="fa-solid fa-user-shield"></i> بريد أو هاتف مسؤول الإدارة';
            input.placeholder = 'admin@gmail.com أو 01XXXXXXXXX';
        }
        input.value = '';
        if (pwd) pwd.value = '';
    }

    // التبديل بين شاشتي تسجيل الدخول وإنشاء حساب جديد
    switchAuthMode(mode) {
        document.querySelectorAll('.auth-mode-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.auth-sub-view').forEach(view => view.classList.remove('active'));

        const targetBtn = document.getElementById(`tab-btn-${mode}`);
        const targetView = document.getElementById(`auth-box-${mode}`);
        if (targetBtn) targetBtn.classList.add('active');
        if (targetView) targetView.classList.add('active');
    }

    // اختيار نوع الحساب في شاشة إنشاء الحساب
    selectRegisterRole(role) {
        document.querySelectorAll('.reg-role-btn').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-reg-role') === role);
        });

        const driverFields = document.getElementById('driver-specific-fields');
        const adminField = document.getElementById('admin-security-field');

        if (driverFields) {
            driverFields.style.display = (role === 'driver') ? 'block' : 'none';
        }
        if (adminField) {
            adminField.style.display = (role === 'admin') ? 'block' : 'none';
        }
    }

    requestAdminAccess() {
        this.notify('🔒 لوحة إدارة المحطة محمية: يرجى تسجيل الدخول ببيانات مسؤول المحطة المعتمد', 'info');
        this.selectLoginRole('admin');
        this.openModal('login-modal');
    }

    // معالجة تسجيل مستخدم جديد بالبيانات الكاملة (الاسم الأول، الأخير، الهاتف، الجيميل، العنوان)
    async handleRegisterSubmit(e) {
        e.preventDefault();

        const activeRegRoleBtn = document.querySelector('.reg-role-btn.active');
        const role = activeRegRoleBtn ? activeRegRoleBtn.getAttribute('data-reg-role') : 'customer';

        const firstName = document.getElementById('reg-first-name').value.trim();
        const lastName = document.getElementById('reg-last-name').value.trim();
        const phone = document.getElementById('reg-phone').value.trim();
        const email = document.getElementById('reg-email').value.trim();
        const address = document.getElementById('reg-address').value.trim();
        const password = document.getElementById('reg-password').value;
        const confirmPassword = document.getElementById('reg-confirm-password').value;
        const licenseNumber = document.getElementById('reg-license') ? document.getElementById('reg-license').value.trim() : '';
        const busNumber = document.getElementById('reg-bus') ? document.getElementById('reg-bus').value.trim() : '';

        // التحقق من كود أمان الإدارة في حال كان التسجيل كمسؤول
        let adminCode = '';
        if (role === 'admin') {
            const adminInput = document.getElementById('reg-admin-code');
            adminCode = adminInput ? adminInput.value.trim() : '';
            if (!adminCode) {
                this.notify('⛔ يرجى إدخال كود تفويض إدارة المحطة لمنع التسجيل غير المصرح به!', 'error');
                return;
            }
        }

        if (password !== confirmPassword) {
            this.notify('كلمة المرور وتأكيد كلمة المرور غير متطابقين!', 'error');
            return;
        }

        const payload = {
            first_name: firstName,
            last_name: lastName,
            phone: phone,
            email: email,
            address: address,
            password: password,
            role: role,
            license_number: licenseNumber,
            bus_number: busNumber,
            admin_security_code: adminCode
        };

        if (this.isBackendConnected) {
            const res = await this.apiRequest('/auth/register', 'POST', payload);
            if (res && res.success) {
                this.currentUser = res.user;
                this.saveLocalState();
                this.updateUserUI();
                this.closeModal('login-modal');
                this.notify(res.message || `مرحباً بك يا ${firstName}! تم إنشاء حسابك بنجاح.`, 'success');

                if (role === 'driver') this.switchView('driver-view');
                else if (role === 'admin') this.switchView('admin-view');
                else this.switchView('customer-view');
                return;
            } else {
                this.notify((res && res.error) ? res.error : 'فشل إنشاء الحساب! يرجى مراجعة البيانات المدخلة.', 'error');
                return;
            }
        }

        // في حال العمل دون اتصال بالخادم (Offline Fallback)
        this.currentUser = {
            id: Date.now(),
            first_name: firstName,
            last_name: lastName,
            name: `${firstName} ${lastName}`,
            email: email,
            phone: phone,
            address: address,
            role: role,
            license_number: licenseNumber,
            bus_number: busNumber
        };
        this.saveLocalState();
        this.updateUserUI();
        this.closeModal('login-modal');
        this.notify(`🎉 مرحباً بك يا ${firstName}! تم إنشاء حسابك بنجاح.`, 'success');

        if (role === 'driver') this.switchView('driver-view');
        else if (role === 'admin') this.switchView('admin-view');
        else this.switchView('customer-view');
    }

    // معالجة تسجيل الدخول الحقيقي
    async handleLoginSubmit(e) {
        e.preventDefault();
        const activeRoleBtn = document.querySelector('.role-btn.active');
        const role = activeRoleBtn ? activeRoleBtn.getAttribute('data-role') : 'customer';
        const identifier = document.getElementById('login-identifier').value.trim();
        const password = document.getElementById('login-password').value;

        if (this.isBackendConnected) {
            const res = await this.apiRequest('/auth/login', 'POST', { identifier, password, role });
            if (res && res.success) {
                this.currentUser = res.user;
                this.saveLocalState();
                this.updateUserUI();
                this.closeModal('login-modal');
                this.notify(res.message || `مرحباً بك مجدداً ${this.currentUser.name}`, 'success');

                if (this.currentUser.role === 'driver') this.switchView('driver-view');
                else if (this.currentUser.role === 'admin') this.switchView('admin-view');
                else this.switchView('customer-view');
                return;
            } else {
                this.notify((res && res.error) ? res.error : 'بيانات تسجيل الدخول غير صحيحة، يرجى التأكد من البريد أو الهاتف وكلمة المرور', 'error');
                return;
            }
        }

        this.notify('بيانات تسجيل الدخول غير صحيحة، يرجى التأكد من البريد وكلمة المرور', 'error');
    }

    // ==================== البحث وعرض الرحلات ====================
    setupEventListeners() {
        const searchBtn = document.getElementById('btn-search-trips');
        if (searchBtn) searchBtn.addEventListener('click', () => this.handleSearch());

        document.querySelectorAll('.filter-pills .pill').forEach(pill => {
            pill.addEventListener('click', () => {
                document.querySelectorAll('.filter-pills .pill').forEach(p => p.classList.remove('active'));
                pill.classList.add('active');
                this.currentFilter = pill.getAttribute('data-filter');
                this.renderTrips();
            });
        });
    }

    async handleSearch() {
        const origin = document.getElementById('search-origin').value;
        const dest = document.getElementById('search-dest').value;

        if (origin === dest) {
            this.notify('لا يمكن أن تكون محطة الانطلاق هي نفس محطة الوصول!', 'error');
            return;
        }

        if (this.isBackendConnected) {
            const res = await this.apiRequest(`/trips?from=${encodeURIComponent(origin)}&to=${encodeURIComponent(dest)}`);
            if (res && res.success) {
                const filtered = res.trips.map(t => this.mapApiTrip(t));
                this.renderTrips(filtered);
                this.notify(`تم جلب ${filtered.length} رحلة من قاعدة البيانات`, 'info');
                return;
            }
        }

        const filtered = this.trips.filter(t => t.from === origin && t.to === dest);
        this.renderTrips(filtered);
        this.notify(`تم العثور على ${filtered.length} رحلة`, 'info');
    }

    renderTrips(customList = null) {
        const container = document.getElementById('trips-list-container');
        if (!container) return;

        let list = customList || this.trips;
        if (this.currentFilter && this.currentFilter !== 'all') {
            list = list.filter(t => t.busClass === this.currentFilter);
        }

        const countLabel = document.getElementById('trips-count-label');
        if (countLabel) countLabel.textContent = `متوفر الآن ${list.length} رحلة مجدولة`;

        if (list.length === 0) {
            container.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 40px; background: #fff; border-radius: 12px; border: 1px dashed var(--border);">
                    <i class="fa-solid fa-bus" style="font-size: 40px; color: #94a3b8; margin-bottom: 12px;"></i>
                    <h4>لا توجد رحلات مطابقة لبحثك في الوقت الحالي</h4>
                    <button class="btn-primary-action" style="margin-top: 15px;" onclick="app.renderTrips()">عرض جميع الرحلات</button>
                </div>
            `;
            return;
        }

        container.innerHTML = list.map(trip => {
            const availableSeats = trip.totalSeats - trip.bookedSeats.length;
            const badgeClass = trip.busClass === 'VIP' ? 'badge-vip' : (trip.busClass === 'Business' ? 'badge-business' : 'badge-standard');

            return `
                <div class="trip-card">
                    <div>
                        <div class="trip-card-header">
                            <span class="trip-class-badge ${badgeClass}"><i class="fa-solid fa-star"></i> ${trip.busClassLabel}</span>
                            <span class="trip-bus-code">كود: ${trip.id}</span>
                        </div>
                        <div class="trip-route-display">
                            <div class="route-stop">
                                <div class="time">${trip.departureTimeLabel}</div>
                                <div class="station">${trip.from}</div>
                                <small style="font-size: 11px; color: #94a3b8;">${trip.fromStation}</small>
                            </div>
                            <div class="route-duration-line">
                                <span class="duration-text">${trip.duration}</span>
                                <div class="line"></div>
                            </div>
                            <div class="route-stop">
                                <div class="time">${trip.arrivalTimeLabel}</div>
                                <div class="station">${trip.to}</div>
                                <small style="font-size: 11px; color: #94a3b8;">${trip.toStation}</small>
                            </div>
                        </div>
                        <div style="font-size: 12px; color: var(--muted); margin-bottom: 14px;">
                            <div><i class="fa-solid fa-bus"></i> ${trip.busNumber}</div>
                            <div><i class="fa-solid fa-user-tie"></i> الكابتن: ${trip.driverName}</div>
                        </div>
                    </div>
                    <div class="trip-card-footer">
                        <div class="trip-price-box">
                            <small>سعر التذكرة</small>
                            <span class="price">${trip.price} <small style="font-size: 14px;">ج.م</small></span>
                            <span class="seats-remaining ${availableSeats < 5 ? 'low' : ''}">
                                <i class="fa-solid fa-couch"></i> متبقي ${availableSeats} مقعد
                            </span>
                        </div>
                        <button class="btn-primary-action" onclick="app.openSeatModal('${trip.id}')" ${availableSeats === 0 ? 'disabled' : ''}>
                            <i class="fa-solid fa-couch"></i> ${availableSeats === 0 ? 'اكتملت المقاعد' : 'اختيار المقاعد'}
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    // ==================== خريطة المقاعد التفاعلية ====================
    async openSeatModal(tripId) {
        if (this.isBackendConnected) {
            const res = await this.apiRequest(`/trips/${tripId}`);
            if (res && res.success) {
                this.selectedTrip = this.mapApiTrip(res.trip);
            } else {
                this.selectedTrip = this.trips.find(t => t.id === tripId);
            }
        } else {
            this.selectedTrip = this.trips.find(t => t.id === tripId);
        }

        if (!this.selectedTrip) return;
        this.selectedSeats = [];

        document.getElementById('seat-modal-trip-title').textContent = `حجز مقاعد رحلة: ${this.selectedTrip.from} ⬅️ ${this.selectedTrip.to}`;
        document.getElementById('seat-modal-trip-subtitle').textContent = `موعد المغادرة: ${this.selectedTrip.departureTimeLabel} | ${this.selectedTrip.busNumber}`;
        document.getElementById('summary-single-price').textContent = this.selectedTrip.price;

        this.renderBusSeats();
        this.updateSeatSummary();
        this.openModal('seat-modal');
    }

    renderBusSeats() {
        const grid = document.getElementById('bus-seats-grid');
        grid.innerHTML = '';
        const rows = Math.ceil(this.selectedTrip.totalSeats / 4);

        for (let r = 0; r < rows; r++) {
            const rowDiv = document.createElement('div');
            rowDiv.className = 'seat-row';

            const rightPair = document.createElement('div');
            rightPair.className = 'seat-pair';
            rightPair.appendChild(this.createSeatElement((r * 4) + 1));
            rightPair.appendChild(this.createSeatElement((r * 4) + 2));

            const aisle = document.createElement('div');
            aisle.className = 'bus-aisle';
            aisle.textContent = `صف ${r + 1}`;

            const leftPair = document.createElement('div');
            leftPair.className = 'seat-pair';
            leftPair.appendChild(this.createSeatElement((r * 4) + 3));
            leftPair.appendChild(this.createSeatElement((r * 4) + 4));

            rowDiv.appendChild(rightPair);
            rowDiv.appendChild(aisle);
            rowDiv.appendChild(leftPair);
            grid.appendChild(rowDiv);
        }
    }

    createSeatElement(seatNumber) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'seat-btn';
        btn.textContent = seatNumber;

        const isBooked = this.selectedTrip.bookedSeats.includes(seatNumber);
        if (isBooked) {
            btn.classList.add('booked');
            btn.title = `المقعد ${seatNumber} محجوز مسبقاً`;
        } else {
            btn.title = `انقر لاختيار مقعد ${seatNumber}`;
            btn.addEventListener('click', () => this.toggleSeat(seatNumber, btn));
        }
        return btn;
    }

    toggleSeat(seatNumber, btnElement) {
        const index = this.selectedSeats.indexOf(seatNumber);
        if (index > -1) {
            this.selectedSeats.splice(index, 1);
            btnElement.classList.remove('selected');
        } else {
            this.selectedSeats.push(seatNumber);
            btnElement.classList.add('selected');
        }
        this.updateSeatSummary();
    }

    updateSeatSummary() {
        const listEl = document.getElementById('summary-seats-list');
        const totalEl = document.getElementById('summary-total-price');
        const proceedBtn = document.getElementById('btn-proceed-to-pay');

        if (this.selectedSeats.length === 0) {
            listEl.textContent = 'لم يتم تحديد مقاعد';
            totalEl.textContent = '0';
            proceedBtn.disabled = true;
        } else {
            this.selectedSeats.sort((a,b) => a - b);
            listEl.textContent = this.selectedSeats.join(' ، ');
            totalEl.textContent = this.selectedSeats.length * this.selectedTrip.price;
            proceedBtn.disabled = false;
        }
    }

    // ==================== الدفع وتأكيد الحجز عبر الباك إند ====================
    proceedToPayment() {
        if (this.selectedSeats.length === 0) return;
        this.closeModal('seat-modal');

        document.getElementById('pay-summary-route').textContent = `${this.selectedTrip.from} ⬅️ ${this.selectedTrip.to} (${this.selectedTrip.departureTimeLabel})`;
        document.getElementById('pay-summary-seats').textContent = `مقاعد: [ ${this.selectedSeats.join(' ، ')} ]`;
        document.getElementById('pay-summary-amount').textContent = `${this.selectedSeats.length * this.selectedTrip.price} ج.م`;

        if (this.currentUser) {
            document.getElementById('cust-name').value = this.currentUser.name || '';
            document.getElementById('cust-phone').value = this.currentUser.phone || '';
        }
        this.openModal('payment-modal');
    }

    togglePaymentTab(method) {
        document.querySelectorAll('.pay-subtab').forEach(tab => tab.classList.remove('active'));
        const activeSubtab = document.getElementById(`pay-tab-${method}`);
        if (activeSubtab) activeSubtab.classList.add('active');

        const confirmBtn = document.getElementById('btn-confirm-payment');
        if (method === 'cash') {
            confirmBtn.innerHTML = '<i class="fa-solid fa-clock"></i> تأكيد الحجز المبدئي (دفع بالمحطة)';
        } else {
            confirmBtn.innerHTML = '<i class="fa-solid fa-lock"></i> إتمام الدفع الإلكتروني وتأكيد الحجز';
        }
    }

    async handlePaymentSubmit(e) {
        e.preventDefault();

        const name = document.getElementById('cust-name').value.trim();
        const phone = document.getElementById('cust-phone').value.trim();
        const natId = document.getElementById('cust-national-id').value.trim();
        const method = document.querySelector('input[name="payment_method"]:checked').value;

        if (!name || !phone) {
            this.notify('يرجى ملء اسم المسافر ورقم الهاتف', 'error');
            return;
        }

        const payload = {
            trip_id: this.selectedTrip.id,
            customer_name: name,
            customer_phone: phone,
            national_id: natId || '---',
            seats: [...this.selectedSeats],
            payment_method: method
        };

        // إرسال الطلب للباك إند
        if (this.isBackendConnected) {
            const res = await this.apiRequest('/bookings', 'POST', payload);
            if (res && res.success) {
                this.closeModal('payment-modal');
                this.notify('🎉 تم تسجيل الحجز وسداد الأجرة في قاعدة البيانات!', 'success');
                
                // تحديث البيانات من الخادم
                await this.loadInitialData();
                this.renderTrips();
                this.renderCustomerBookings();
                this.renderDriverPortal();
                this.renderAdminDashboard();

                this.openTicketModal(res.ticket, this.selectedTrip);
                return;
            } else if (res && res.error) {
                this.notify(res.error, 'error');
                return;
            }
        }

        // في حال العمل المحلي (Offline Fallback)
        const pnr = 'EXP-' + Math.floor(10000 + Math.random() * 90000);
        const total = this.selectedSeats.length * this.selectedTrip.price;
        const newBooking = {
            pnr: pnr,
            tripId: this.selectedTrip.id,
            customerName: name,
            customerPhone: phone,
            nationalId: natId || '---',
            seats: [...this.selectedSeats],
            totalAmount: total,
            paymentMethod: method,
            paymentStatus: method === 'cash' ? 'pending_cash' : 'paid',
            bookingDate: new Date().toLocaleString('ar-EG'),
            boarded: false,
            route: `${this.selectedTrip.from} ⬅️ ${this.selectedTrip.to}`,
            departureTimeLabel: this.selectedTrip.departureTimeLabel
        };

        this.selectedTrip.bookedSeats.push(...this.selectedSeats);
        this.bookings.unshift(newBooking);
        this.saveLocalState();

        this.closeModal('payment-modal');
        this.notify('🎉 تم تأكيد حجزك بنجاح!', 'success');
        this.openTicketModal(newBooking, this.selectedTrip);
        this.renderTrips();
        this.renderCustomerBookings();
    }

    // ==================== عرض وطباعة التذكرة ====================
    openTicketModal(booking, trip = null) {
        if (!trip) {
            trip = this.trips.find(t => t.id === (booking.trip_id || booking.tripId)) || this.trips[0];
        }

        document.getElementById('tkt-from').textContent = trip.from;
        document.getElementById('tkt-from-station').textContent = trip.fromStation;
        document.getElementById('tkt-to').textContent = trip.to;
        document.getElementById('tkt-to-station').textContent = trip.toStation;
        document.getElementById('tkt-bus-class').textContent = trip.busClassLabel;
        document.getElementById('tkt-passenger-name').textContent = booking.customer_name || booking.customerName;
        document.getElementById('tkt-passenger-phone').textContent = booking.customer_phone || booking.customerPhone;
        document.getElementById('tkt-date').textContent = trip.date;
        document.getElementById('tkt-time').textContent = trip.departureTimeLabel;
        document.getElementById('tkt-seats').textContent = (booking.seats || []).join(' ، ');
        document.getElementById('tkt-bus-plate').textContent = trip.busNumber;
        document.getElementById('tkt-price').textContent = `${booking.total_amount || booking.totalAmount} ج.م`;
        document.getElementById('tkt-pnr').textContent = booking.pnr;

        const badge = document.getElementById('ticket-status-badge');
        const isPaid = (booking.payment_status || booking.paymentStatus) === 'paid';
        if (isPaid) {
            badge.className = 'ticket-badge-paid';
            badge.style.background = '#10b981';
            badge.innerHTML = '<i class="fa-solid fa-check"></i> مؤكدة ومدفوعة بالكامل';
        } else {
            badge.className = 'ticket-badge-paid';
            badge.style.background = '#d97706';
            badge.innerHTML = '<i class="fa-solid fa-clock"></i> في انتظار السداد بالمحطة';
        }

        this.openModal('ticket-modal');
    }

    renderCustomerBookings() {
        const container = document.getElementById('customer-tickets-list');
        if (!container) return;

        if (this.bookings.length === 0) {
            container.innerHTML = `<p style="color: var(--muted); font-size: 13px;">لا توجد لديك حجوزات مسجلة حالياً.</p>`;
            return;
        }

        container.innerHTML = this.bookings.map(b => {
            const isPaid = b.paymentStatus === 'paid' || b.payment_status === 'paid';
            const badgeBg = isPaid ? '#dcfce7' : '#fef3c7';
            const badgeColor = isPaid ? '#166534' : '#92400e';
            const badgeLabel = isPaid ? 'مدفوعة' : 'دفع بالمحطة';

            return `
            <div class="mini-ticket-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong><i class="fa-solid fa-ticket"></i> ${b.pnr}</strong>
                    <span style="font-size:11px; padding:3px 10px; border-radius:12px; background:${badgeBg}; color:${badgeColor}; font-weight:700;">
                        ${badgeLabel}
                    </span>
                </div>
                <div style="font-size:13.5px; font-weight:800; margin: 6px 0;">${b.route}</div>
                <div style="font-size:12px; color:var(--muted);">
                    <span>مقاعد: ${(b.seats || []).join(',')}</span> | 
                    <span>المبلغ: <strong>${b.totalAmount || b.total_amount} ج.م</strong></span>
                </div>
                <div style="display:flex; gap:8px; margin-top:8px;">
                    <button class="btn-secondary-action" style="padding:5px 12px; font-size:12px;" onclick="app.viewTicketByPNR('${b.pnr}')">
                        <i class="fa-solid fa-eye"></i> عرض بطاقة التذكرة والـ QR
                    </button>
                </div>
            </div>
            `;
        }).join('');
    }

    viewTicketByPNR(pnr) {
        const booking = this.bookings.find(b => b.pnr === pnr);
        if (booking) this.openTicketModal(booking);
    }

    // ==================== بوابة السائق وتأكيد الصعود ====================
    async renderDriverPortal() {
        const driverTrips = this.trips.filter(t => t.driverName.includes('محمود'));
        const activeTrip = driverTrips[0] || this.trips[0];

        if (activeTrip) {
            document.getElementById('current-trip-title').textContent = `رحلة رقم #${activeTrip.id}: ${activeTrip.from} ⬅️ ${activeTrip.to}`;
            document.getElementById('current-trip-time').innerHTML = `<i class="fa-regular fa-clock"></i> موعد المغادرة: ${activeTrip.departureTimeLabel} | ${activeTrip.fromStation} | ${activeTrip.busNumber}`;

            const statusEl = document.getElementById('current-trip-status');
            if (activeTrip.status === 'active') {
                statusEl.textContent = '🟢 الحافلة في الطريق الآن';
                statusEl.className = 'status-tag status-in-progress';
            } else if (activeTrip.status === 'completed') {
                statusEl.textContent = '🏁 انتهت الرحلة وتم الوصول';
                statusEl.className = 'status-tag status-completed';
            } else {
                statusEl.textContent = '🟡 جاهزة للانطلاق والصعود';
                statusEl.className = 'status-tag status-in-progress';
            }

            this.renderDriverPassengers(activeTrip.id);
        }
    }

    renderDriverPassengers(tripId) {
        const tbody = document.getElementById('driver-passenger-tbody');
        if (!tbody) return;

        const tripBookings = this.bookings.filter(b => (b.tripId || b.trip_id) === tripId);
        if (tripBookings.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--muted);">لا يوجد ركاب مسجلين حتى الآن</td></tr>`;
            return;
        }

        tbody.innerHTML = tripBookings.map(b => `
            <tr>
                <td><strong style="color:var(--primary); font-size:15px;">${(b.seats || []).join(' ، ')}</strong></td>
                <td><strong>${b.customerName || b.customer_name}</strong></td>
                <td>${b.customerPhone || b.customer_phone}</td>
                <td><span style="font-family:monospace; color:#b45309;">${b.pnr}</span></td>
                <td>${(b.paymentStatus || b.payment_status) === 'paid' ? 'مدفوع' : 'نقداً'}</td>
                <td>
                    <span style="padding:3px 8px; border-radius:12px; font-size:11px; font-weight:700; background:${b.boarded ? '#dcfce7':'#fee2e2'}; color:${b.boarded ? '#166534':'#991b1b'};">
                        ${b.boarded ? '✅ صعد للحافلة' : '❌ لم يصعد بعد'}
                    </span>
                </td>
                <td>
                    <button class="btn-checkin-action ${b.boarded ? 'checked' : ''}" onclick="app.togglePassengerBoarding('${b.pnr}')">
                        ${b.boarded ? 'تم التأكيد' : 'تأكيد صعود الراكب'}
                    </button>
                </td>
            </tr>
        `).join('');
    }

    async togglePassengerBoarding(pnr) {
        if (this.isBackendConnected) {
            const res = await this.apiRequest('/driver/checkin', 'POST', { pnr: pnr });
            if (res && res.success) {
                const b = this.bookings.find(bk => bk.pnr === pnr);
                if (b) b.boarded = res.boarded === 1;
                this.renderDriverPassengers(b ? (b.tripId || b.trip_id) : this.trips[0].id);
                this.notify(res.boarded === 1 ? 'تم تسجيل صعود الراكب بنجاح في قاعدة البيانات' : 'تم إلغاء حالة الصعود', 'info');
                return;
            }
        }

        const booking = this.bookings.find(b => b.pnr === pnr);
        if (booking) {
            booking.boarded = !booking.boarded;
            this.saveLocalState();
            this.renderDriverPassengers(booking.tripId || booking.trip_id);
            this.notify(booking.boarded ? 'تم تأكيد صعود الراكب' : 'تم إلغاء التأكيد', 'info');
        }
    }

    async updateTripStatus(newStatus) {
        const activeTrip = this.trips[0];
        if (!activeTrip) return;

        if (this.isBackendConnected) {
            await this.apiRequest('/driver/trip-status', 'POST', { trip_id: activeTrip.id, status: newStatus });
        }
        activeTrip.status = newStatus;
        this.saveLocalState();
        this.renderDriverPortal();
        this.notify(`تم تحديث حالة الرحلة إلى: ${newStatus === 'active' ? 'في الطريق' : 'انتهت'}`, 'success');
    }

    // ==================== لوحة تحكم الإدارة (Admin) ====================
    async renderAdminDashboard() {
        if (this.isBackendConnected) {
            const res = await this.apiRequest('/admin/stats');
            if (res && res.success) {
                const st = res.stats;
                document.getElementById('stat-total-revenue').textContent = `${st.total_revenue.toLocaleString()} ج.م`;
                document.getElementById('stat-total-tickets').textContent = st.total_bookings;
                document.getElementById('stat-active-trips').textContent = st.total_trips;
            }
        } else {
            const totalRev = this.bookings.reduce((sum, b) => sum + (b.paymentStatus === 'paid' ? b.totalAmount : 0), 0);
            document.getElementById('stat-total-revenue').textContent = `${totalRev.toLocaleString()} ج.م`;
            document.getElementById('stat-total-tickets').textContent = this.bookings.length;
            document.getElementById('stat-active-trips').textContent = this.trips.length;
        }

        // جدول الرحلات
        const tripsTbody = document.getElementById('admin-trips-table-body');
        if (tripsTbody) {
            tripsTbody.innerHTML = this.trips.map(tr => `
                <tr>
                    <td><strong>#${tr.id}</strong></td>
                    <td>${tr.from} ⬅️ ${tr.to}</td>
                    <td>${tr.departureTimeLabel}</td>
                    <td>${tr.busClassLabel}</td>
                    <td>${tr.driverName}</td>
                    <td><strong>${tr.price} ج.م</strong></td>
                    <td>
                        <button class="btn-secondary-action" style="padding:4px 8px; font-size:12px; color:var(--danger);" onclick="app.deleteTrip('${tr.id}')">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        }

        // جدول الحجوزات
        const bookingsTbody = document.getElementById('admin-bookings-table-body');
        if (bookingsTbody) {
            bookingsTbody.innerHTML = this.bookings.map(b => `
                <tr>
                    <td><strong style="font-family:monospace; color:var(--primary);">${b.pnr}</strong></td>
                    <td>${b.customerName || b.customer_name}</td>
                    <td>${b.route}</td>
                    <td><strong>${(b.seats || []).join(',')}</strong></td>
                    <td>${b.totalAmount} ج.م</td>
                    <td>${b.paymentMethod}</td>
                    <td>
                        <span style="padding:2px 8px; border-radius:10px; font-size:11px; background:${(b.paymentStatus==='paid')?'#dcfce7':'#fef3c7'}; color:${(b.paymentStatus==='paid')?'#166534':'#92400e'}">
                            ${b.paymentStatus === 'paid' ? 'مدفوع' : 'مطلوب نقداً'}
                        </span>
                    </td>
                </tr>
            `).join('');
        }

        // أسطول السائقين
        const driversContainer = document.getElementById('admin-drivers-fleet-container');
        if (driversContainer) {
            driversContainer.innerHTML = this.drivers.map(d => `
                <div style="background:#f8fafc; border:1px solid var(--border); border-radius:8px; padding:14px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h4 style="font-size:15px; margin-bottom:4px;"><i class="fa-solid fa-id-badge"></i> ${d.name} (${d.id})</h4>
                        <p style="font-size:12px; color:var(--muted);"><i class="fa-solid fa-bus"></i> ${d.bus_info || d.bus} | هاتف: ${d.phone}</p>
                    </div>
                    <span style="background:#fef3c7; color:#b45309; padding:2px 8px; border-radius:12px; font-size:12px; font-weight:700;">★ ${d.rating}</span>
                </div>
            `).join('');
        }
    }

    switchAdminTab(tabName, evt) {
        document.querySelectorAll('.admin-tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.admin-tab-content').forEach(content => content.classList.remove('active'));

        const currentTarget = (evt && evt.currentTarget) || (typeof event !== 'undefined' && event && event.currentTarget) || document.querySelector(`.admin-tab-btn[data-admin-tab="${tabName}"]`);
        if (currentTarget) currentTarget.classList.add('active');
        const target = document.getElementById(`admin-tab-${tabName}`);
        if (target) target.classList.add('active');
    }

    openNewTripModal() { this.openModal('new-trip-modal'); }

    async handleNewTripSubmit(e) {
        e.preventDefault();

        const from = document.getElementById('new-trip-from').value;
        const to = document.getElementById('new-trip-to').value;
        const date = document.getElementById('new-trip-date').value;
        const time = document.getElementById('new-trip-time').value;
        const price = parseInt(document.getElementById('new-trip-price').value);
        const busClass = document.getElementById('new-trip-class').value;
        const driverName = document.getElementById('new-trip-driver').value;
        const busNumber = document.getElementById('new-trip-bus').value;

        if (from === to) {
            this.notify('محطة الانطلاق لا يمكن أن تكون نفس محطة الوصول', 'error');
            return;
        }

        const newTripData = {
            from_city: from,
            to_city: to,
            departure_time: time,
            trip_date: date,
            price: price,
            bus_class: busClass,
            driver_name: driverName,
            bus_number: busNumber
        };

        if (this.isBackendConnected) {
            const res = await this.apiRequest('/trips', 'POST', newTripData);
            if (res && res.success) {
                this.closeModal('new-trip-modal');
                await this.loadInitialData();
                this.renderTrips();
                this.renderAdminDashboard();
                this.notify('تمت جدولة الرحلة بنجاح في قاعدة بيانات SQLite!', 'success');
                return;
            }
        }

        const newId = 'EX-' + Math.floor(800 + Math.random() * 200);
        this.trips.unshift({
            id: newId,
            from: from,
            fromStation: `موقف ${from}`,
            to: to,
            toStation: `موقف ${to}`,
            departureTime: time,
            departureTimeLabel: time,
            arrivalTimeLabel: 'بعد 4 ساعات',
            duration: '4 ساعات تقريباً',
            date: date,
            price: price,
            busClass: busClass,
            busClassLabel: busClass,
            busNumber: busNumber,
            driverName: driverName,
            totalSeats: 28,
            bookedSeats: [],
            status: 'ready'
        });

        this.saveLocalState();
        this.closeModal('new-trip-modal');
        this.renderTrips();
        this.renderAdminDashboard();
        this.notify('تمت إضافة الرحلة للجدول', 'success');
    }

    async deleteTrip(tripId) {
        if (!confirm(`هل أنت متأكد من حذف الرحلة #${tripId}؟`)) return;

        if (this.isBackendConnected) {
            await this.apiRequest(`/trips/${tripId}`, 'DELETE');
        }

        this.trips = this.trips.filter(t => t.id !== tripId);
        this.saveLocalState();
        this.renderTrips();
        this.renderAdminDashboard();
        this.notify('تم حذف الرحلة', 'info');
    }

    // ==================== النوافذ والإشعارات ====================
    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('show');
            document.body.style.overflow = 'hidden';
        }
    }

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('show');
            document.body.style.overflow = '';
        }
    }

    notify(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        let icon = 'fa-circle-info';
        if (type === 'success') icon = 'fa-circle-check';
        if (type === 'error') icon = 'fa-triangle-exclamation';

        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(-100%)';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }
}

const app = new BusStationApp();
document.addEventListener('DOMContentLoaded', () => app.init());
