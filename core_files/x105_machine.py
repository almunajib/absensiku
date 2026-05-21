from zk import ZK, const
from datetime import datetime


class X105Client:
    def __init__(self, ip="192.168.1.33", port=4370, password="", sn=None, timeout=10):
        self.ip = ip
        self.port = port
        self.password = password
        self.sn = sn if sn else ip  # default pakai IP kalau SN tidak diketahui
        self.timeout = timeout
        self.zk = ZK(
            self.ip,
            port=self.port,
            timeout=self.timeout,
            password=self.password,
            force_udp=False,
            ommit_ping=False,
        )
        self.conn = None

    def connect(self):
        try:
            self.conn = self.zk.connect()
            return True, "Connected"
        except Exception as e:
            return False, str(e)

    def disconnect(self):
        if self.conn:
            try:
                self.conn.disconnect()
            except Exception:
                pass
        self.conn = None
        return True

    def test_connection(self):
        ok, msg = self.connect()
        if not ok:
            return False, msg
        self.disconnect()
        return True, "Connected"

    # ============================================
    # USER MANAGEMENT
    # ============================================
    def get_users(self):
        """Ambil semua user dari mesin"""
        ok, msg = self.connect()
        if not ok:
            return [], msg

        try:
            users = self.conn.get_users()
            user_list = []
            for user in users:
                user_list.append(
                    {
                        "uid": user.uid,
                        "user_id": user.user_id,
                        "name": user.name,
                        "privilege": user.privilege,
                        "password": user.password,
                        "group_id": user.group_id,
                        "card": user.card,
                    }
                )
            self.disconnect()
            return user_list, f"Success ({len(user_list)} users)"
        except Exception as e:
            self.disconnect()
            return [], f"Error: {str(e)}"

    def add_user(self, user_id, name, privilege=0, group_id="", card=0, password=""):
        """Tambah user baru ke mesin"""
        ok, msg = self.connect()
        if not ok:
            return False, f"Connection failed: {msg}"

        try:
            # Langsung set user tanpa enable/disable
            self.conn.set_user(
                user_id=str(user_id),
                name=str(name),
                privilege=int(privilege),
                group_id=str(group_id),
                card=int(card),
                password=str(password),
            )

            self.disconnect()
            return True, f"User '{name}' (ID: {user_id}) berhasil ditambahkan"

        except Exception as e:
            self.disconnect()
            return False, f"Error: {str(e)}"

    def update_user(
        self,
        user_id,
        name=None,
        privilege=None,
        password=None,
        group_id=None,
        card=None,
    ):
        """
        Update user yang sudah ada

        Args:
            user_id: ID user yang akan diupdate
            name: Nama baru (optional)
            privilege: Privilege baru (optional)
            password: Password baru (optional)
            group_id: Group ID baru (optional)
            card: Card number baru (optional)
        """
        ok, msg = self.connect()
        if not ok:
            return False, f"Connection failed: {msg}"

        try:
            # Ambil user yang ada
            users = self.conn.get_users()
            target_user = None

            for user in users:
                if user.user_id == str(user_id):
                    target_user = user
                    break

            if not target_user:
                self.disconnect()
                return False, f"User ID {user_id} tidak ditemukan"

            # Update user dengan data baru atau tetap pakai yang lama
            self.conn.set_user(
                uid=target_user.uid,  # penting supaya update, bukan insert baru
                user_id=str(user_id),
                name=str(name) if name is not None else target_user.name,
                privilege=int(privilege)
                if privilege is not None
                else target_user.privilege,
                password=str(password)
                if password is not None
                else target_user.password,
                group_id=str(group_id)
                if group_id is not None
                else target_user.group_id,
                card=int(card) if card is not None else target_user.card,
            )

            self.disconnect()
            return True, f"User ID {user_id} berhasil diupdate"

        except Exception as e:
            self.disconnect()
            return False, f"Error: {str(e)}"

    def delete_user(self, user_id):
        """
        Hapus user dari mesin

        Args:
            user_id: ID user yang akan dihapus
        """
        ok, msg = self.connect()
        if not ok:
            return False, f"Connection failed: {msg}"

        try:
            # Ambil user untuk dapat uid
            users = self.conn.get_users()
            target_uid = None
            target_name = None

            for user in users:
                if user.user_id == str(user_id):
                    target_uid = user.uid
                    target_name = user.name
                    break

            if target_uid is None:
                self.disconnect()
                return False, f"User ID {user_id} tidak ditemukan"

            # Delete user
            self.conn.delete_user(uid=target_uid, user_id=str(user_id))

            self.disconnect()
            return True, f"User '{target_name}' (ID: {user_id}) berhasil dihapus"

        except Exception as e:
            self.disconnect()
            return False, f"Error: {str(e)}"

    # ============================================
    # LOG MANAGEMENT
    # ============================================
    def get_attendance_logs(self):
        ok, msg = self.connect()
        if not ok:
            return [], msg

        logs = []
        try:
            # coba ambil SN mesin
            device_sn = None
            try:
                device_sn = self.conn.get_serialnumber()
            except Exception as e:
                print(
                    f"⚠️ Warning: gagal ambil SN dari device {self.ip}:{self.port} → {e}"
                )
                device_sn = "UNKNOWN"

            attendances = self.conn.get_attendance()
            for att in attendances:
                logs.append(
                    {
                        "userid": str(att.user_id),
                        "checktime": att.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "verifycode": getattr(att, "punch", 0),
                        "workcode": getattr(att, "work_code", 0),
                        "sn": device_sn,
                    }
                )

            self.disconnect()
            return logs, f"Success ({len(logs)} records)"

        except Exception as e:
            self.disconnect()
            return [], f"Exception while reading logs: {e}"

    # ============================================
    # CLEAR DATA
    # ============================================
    def clear_attendance(self):
        """Hapus semua attendance logs"""
        ok, msg = self.connect()
        if not ok:
            return False, msg

        try:
            self.conn.enable_device()
            self.conn.clear_attendance()
            self.conn.disable_device()
            self.disconnect()
            return True, "Attendance logs berhasil dihapus"
        except Exception as e:
            self.disconnect()
            return False, f"Error: {str(e)}"

    # ============================================
    # DEVICE CONTROL
    # ============================================

    def sync_time(self, new_time=None):
        """
        Sinkronkan waktu mesin dengan waktu PC/server.
        Jika new_time=None, otomatis pakai waktu sekarang (localtime).
        """
        ok, msg = self.connect()
        if not ok:
            return False, msg

        try:
            if new_time is None:
                new_time = datetime.now()

            self.conn.set_time(new_time)
            self.disconnect()
            return (
                True,
                f"Waktu mesin berhasil disinkronkan ke {new_time.strftime('%Y-%m-%d %H:%M:%S')}",
            )
        except Exception as e:
            self.disconnect()
            return False, f"Error: {str(e)}"

    def restart_device(self):
        """Restart mesin"""
        ok, msg = self.connect()
        if not ok:
            return False, msg

        try:
            self.conn.restart()
            self.disconnect()
            return True, "Device restarted successfully"
        except Exception as e:
            self.disconnect()
            return False, f"Error: {str(e)}"

    def poweroff_device(self):
        """Matikan mesin"""
        ok, msg = self.connect()
        if not ok:
            return False, msg

        try:
            self.conn.poweroff()
            self.disconnect()
            return True, "Device powered off"
        except Exception as e:
            self.disconnect()
            return False, f"Error: {str(e)}"

    def test_voice(self, index=0):
        """Test suara mesin (index 0-64)"""
        ok, msg = self.connect()
        if not ok:
            return False, msg

        try:
            self.conn.test_voice(index=index)
            self.disconnect()
            return True, f"Voice test {index} berhasil"
        except Exception as e:
            self.disconnect()
            return False, f"Error: {str(e)}"

    # ===========================================
    # INVENTORY DEVICE
    # ===========================================
    def get_firmware_version(self):
        """Get firmware version from the connected device."""
        try:
            firmware = self.conn.get_firmware_version()
            return firmware
        except Exception as e:
            return f"Error: {str(e)}"

    def get_serial_number(self):
        """Get serial number from the connected device."""
        try:
            serial_number = self.conn.get_serial_number()
            return serial_number
        except Exception as e:
            return f"Error: {str(e)}"

    def get_device_info(self):
        """Get device info from the connected device."""
        ok, msg = self.connect()
        if not ok:
            return None, None

        try:
            firmware = self.conn.get_firmware_version()
            sn = self.conn.get_serialnumber()
            self.disconnect()
            return firmware, sn
        except Exception:
            self.disconnect()
            return None, None


    def get_all_info(self):
        """
        Ambil firmware, SN, dan info mesin via read_sizes().
        get_attendance() TIDAK digunakan karena hang pada mesin ini.
        """
        ok, msg = self.connect()
        if not ok:
            return None, None, 0, 0, 0, 0, 0, 0

        try:
            firmware = self.conn.get_firmware_version()
            sn = self.conn.get_serialnumber()
            self.conn.read_sizes()
            user_count = self.conn.users
            fingers = self.conn.fingers
            cards = self.conn.cards
            record_count = self.conn.records
            rec_cap = self.conn.rec_cap
            rec_av = self.conn.rec_av
            self.disconnect()
            return firmware, sn, user_count, fingers, cards, record_count, rec_cap, rec_av
        except Exception:
            self.disconnect()
            return None, None, 0, 0, 0, 0, 0, 0