<?php
/**
 * محطة إكسبريس | Express Bus System - PHP REST API Alternative
 * ملف باك إند بديل بلغة PHP متوافق مع Apache / XAMPP / Nginx
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$db_file = __DIR__ . '/bus_station.db';
try {
    $pdo = new PDO("sqlite:" . $db_file);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => 'فشل الاتصال بقاعدة البيانات: ' . $e->getMessage()], JSON_UNESCAPED_UNICODE);
    exit;
}

$request_uri = $_SERVER['REQUEST_URI'];
$method = $_SERVER['REQUEST_METHOD'];
$path = parse_url($request_uri, PHP_URL_PATH);
$body = json_decode(file_get_contents('php://input'), true) ?? [];

// 1. جلب قائمة الرحلات
if ($method === 'GET' && strpos($path, '/trips') !== false) {
    $from = $_GET['from'] ?? null;
    $to = $_GET['to'] ?? null;

    $sql = "SELECT * FROM trips WHERE 1=1";
    $params = [];
    if ($from) { $sql .= " AND from_city = ?"; $params[] = $from; }
    if ($to) { $sql .= " AND to_city = ?"; $params[] = $to; }
    $sql .= " ORDER BY departure_time ASC";

    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    $trips = $stmt->fetchAll();

    foreach ($trips as &$t) {
        $b_stmt = $pdo->prepare("SELECT seats FROM bookings WHERE trip_id = ?");
        $b_stmt->execute([$t['id']]);
        $seats_rows = $b_stmt->fetchAll();
        $booked = [];
        foreach ($seats_rows as $sr) {
            $arr = json_decode($sr['seats'], true);
            if (is_array($arr)) $booked = array_merge($booked, $arr);
        }
        $t['booked_seats'] = $booked;
    }

    echo json_encode(['success' => true, 'trips' => $trips], JSON_UNESCAPED_UNICODE);
    exit;
}

// 2. إنشاء حجز جديد
if ($method === 'POST' && strpos($path, '/bookings') !== false) {
    $trip_id = $body['trip_id'] ?? null;
    $name = $body['customer_name'] ?? null;
    $phone = $body['customer_phone'] ?? null;
    $seats = $body['seats'] ?? [];
    $method_pay = $body['payment_method'] ?? 'card';

    if (!$trip_id || !$name || !$phone || empty($seats)) {
        http_response_code(400);
        echo json_encode(['error' => 'بيانات الحجز غير مكتملة'], JSON_UNESCAPED_UNICODE);
        exit;
    }

    $t_stmt = $pdo->prepare("SELECT price FROM trips WHERE id = ?");
    $t_stmt->execute([$trip_id]);
    $trip = $t_stmt->fetch();

    $pnr = "EXP-" . rand(10000, 99999);
    $total = count($seats) * $trip['price'];
    $status = ($method_pay === 'cash') ? 'pending_cash' : 'paid';

    $ins = $pdo->prepare("INSERT INTO bookings (pnr, trip_id, customer_name, customer_phone, seats, total_amount, payment_method, payment_status, boarded) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)");
    $ins->execute([$pnr, $trip_id, $name, $phone, json_encode($seats), $total, $method_pay, $status]);

    echo json_encode(['success' => true, 'pnr' => $pnr, 'message' => 'تم الحجز بنجاح'], JSON_UNESCAPED_UNICODE);
    exit;
}

// 3. تأكيد صعود الراكب (للسائق)
if ($method === 'POST' && strpos($path, '/driver/checkin') !== false) {
    $pnr = $body['pnr'] ?? null;
    $chk = $pdo->prepare("SELECT boarded FROM bookings WHERE pnr = ?");
    $chk->execute([$pnr]);
    $row = $chk->fetch();

    if ($row) {
        $new_boarded = $row['boarded'] == 1 ? 0 : 1;
        $upd = $pdo->prepare("UPDATE bookings SET boarded = ? WHERE pnr = ?");
        $upd->execute([$new_boarded, $pnr]);
        echo json_encode(['success' => true, 'boarded' => $new_boarded], JSON_UNESCAPED_UNICODE);
    } else {
        http_response_code(404);
        echo json_encode(['error' => 'التذكرة غير موجودة'], JSON_UNESCAPED_UNICODE);
    }
    exit;
}

echo json_encode(['status' => 'Express Bus Station PHP API is running']);
