// firebase-db.js — الربط مع Firebase (Auth + Firestore) لمحطة إكسبريس
// الاستخدام في index.html (بدل الكود اللي نسخته من Firebase):
//   <script type="module" src="firebase-db.js"></script>
// وبعدها تنادي الدوال من أي مكان عن طريق window.DB

import { initializeApp } from "https://www.gstatic.com/firebasejs/13.0.0/firebase-app.js";
import {
  getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword,
  signOut, onAuthStateChanged
} from "https://www.gstatic.com/firebasejs/13.0.0/firebase-auth.js";
import {
  getFirestore, doc, getDoc, setDoc, addDoc, updateDoc, deleteDoc,
  collection, getDocs, query, where, orderBy, writeBatch, serverTimestamp
} from "https://www.gstatic.com/firebasejs/13.0.0/firebase-firestore.js";

const firebaseConfig = {
  apiKey: "AIzaSyD5SZ47Zinmw5e65_aog-j546IzcpGibig",
  authDomain: "bus-station-d3725.firebaseapp.com",
  projectId: "bus-station-d3725",
  storageBucket: "bus-station-d3725.firebasestorage.app",
  messagingSenderId: "474362018438",
  appId: "1:474362018438:web:9c673288d40c9555122f07"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

// ---------- الحسابات ----------
// التسجيل من الموقع بينشئ "عميل" بس. السائق والإدارة بتتحدد يدوي من Firebase Console
// (غيّر حقل role في users/{uid} إلى driver أو admin).
async function register({ email, password, firstName, lastName, phone, address }) {
  const cred = await createUserWithEmailAndPassword(auth, email, password);
  await setDoc(doc(db, "users", cred.user.uid), {
    firstName, lastName, phone, address: address ?? "",
    email, role: "customer", createdAt: serverTimestamp()
  });
  return cred.user;
}

async function login(email, password) {
  const cred = await signInWithEmailAndPassword(auth, email, password);
  return getProfile(cred.user.uid);
}

const logout = () => signOut(auth);

async function getProfile(uid) {
  const snap = await getDoc(doc(db, "users", uid));
  return snap.exists() ? { uid, ...snap.data() } : null;
}

// يستدعي callback(profile | null) كل ما حالة الدخول تتغير (حتى بعد عمل Refresh)
function onUserChanged(callback) {
  return onAuthStateChanged(auth, async (user) => {
    callback(user ? await getProfile(user.uid) : null);
  });
}

// ---------- الرحلات (الإدارة تكتب، الكل يقرأ) ----------
// trip: { from, to, date:"2026-10-25", time:"14:30", busType, price, driverId, driverName, busNumber, seatsTotal }
async function addTrip(trip) {
  const ref = await addDoc(collection(db, "trips"), { ...trip, createdAt: serverTimestamp() });
  return ref.id;
}

async function listTrips() {
  const snap = await getDocs(query(collection(db, "trips"), orderBy("date")));
  return snap.docs.map(d => ({ id: d.id, ...d.data() }));
}

const updateTrip = (id, data) => updateDoc(doc(db, "trips", id), data);
const deleteTrip = (id) => deleteDoc(doc(db, "trips", id));

// ---------- المقاعد والحجز ----------
// المقاعد المحجوزة في رحلة (للون "محجوز مسبقاً" في خريطة المقاعد)
async function getTakenSeats(tripId) {
  const snap = await getDocs(query(collection(db, "seats"), where("tripId", "==", tripId)));
  return snap.docs.map(d => d.data().seat);
}

// حجز مقاعد: لو مقعد اتحجز قبل كده العملية كلها بتفشل (منع الحجز المزدوج)
// paymentMethod: "card" | "wallet" | "cash" — متخزنش رقم كارت أو CVV أبداً
async function bookSeats({ tripId, seats, passengerName, passengerPhone, nationalId, paymentMethod, amount }) {
  const user = auth.currentUser;
  if (!user) throw new Error("لازم تسجل دخول الأول");

  const batch = writeBatch(db);
  const pnr = "EXP-" + Math.floor(10000 + Math.random() * 90000);

  seats.forEach(seat => {
    batch.set(doc(db, "seats", `${tripId}_${seat}`), { tripId, seat, userId: user.uid });
    batch.set(doc(db, "bookings", `${tripId}_${seat}`), {
      tripId, seat, userId: user.uid, pnr,
      passengerName, passengerPhone, nationalId: nationalId ?? "",
      paymentMethod, amount: amount / seats.length,
      paymentStatus: paymentMethod === "cash" ? "pending" : "paid",
      boarded: false, createdAt: serverTimestamp()
    });
  });

  try {
    await batch.commit();
  } catch (e) {
    throw new Error("أحد المقاعد اتحجز للتو، اختار مقعد تاني");
  }
  return pnr;
}

async function myBookings() {
  const user = auth.currentUser;
  const snap = await getDocs(query(collection(db, "bookings"), where("userId", "==", user.uid)));
  return snap.docs.map(d => ({ id: d.id, ...d.data() }));
}

// للسائق والإدارة: كشف ركاب رحلة
async function tripPassengers(tripId) {
  const snap = await getDocs(query(collection(db, "bookings"), where("tripId", "==", tripId)));
  return snap.docs.map(d => ({ id: d.id, ...d.data() }));
}

// تأكيد صعود راكب (السائق)
const confirmBoarding = (bookingId, boarded = true) =>
  updateDoc(doc(db, "bookings", bookingId), { boarded });

// كل الحجوزات (الإدارة) — لسجل الحجوزات والإيرادات
async function allBookings() {
  const snap = await getDocs(collection(db, "bookings"));
  return snap.docs.map(d => ({ id: d.id, ...d.data() }));
}

window.DB = {
  auth, db, register, login, logout, getProfile, onUserChanged,
  addTrip, listTrips, updateTrip, deleteTrip,
  getTakenSeats, bookSeats, myBookings, tripPassengers, confirmBoarding, allBookings
};
window.dispatchEvent(new Event("db-ready"));
