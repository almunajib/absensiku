document.addEventListener("DOMContentLoaded", () => {
  let attendanceChart, departmentChart;

  const fetchData = async (start = null, end = null) => {
    let url = "/api/dashboard-data";
    if (start && end) {
      url += `?start=${start}&end=${end}`;
    }

    try {
      const response = await fetch(url);
      const data = await response.json();
      updateUI(data);
    } catch (error) {
      console.error("Error fetching data:", error);
    }
  };

  const updateUI = (data) => {
    // Stats
    document.getElementById("totalEmployees").textContent =
      data.stats.total_employees;
    document.getElementById("presentToday").textContent =
      data.stats.present_today;
    document.getElementById("absentToday").textContent =
      data.stats.absent_today;
    document.getElementById("lateToday").textContent = data.stats.late_today;

    // Analytics
    document.getElementById("avgAttendance").textContent =
      `${data.analytics.avg_attendance_rate}%`;
    document.getElementById("peakTime").textContent = data.analytics.peak_time;
    document.getElementById("activeDays").textContent =
      data.analytics.active_days;
    document.getElementById("lateRate").textContent =
      `${data.analytics.late_rate}%`;

    // Recent Activities
    const recentActivitiesBody = document.getElementById("recentActivities");
    recentActivitiesBody.innerHTML = "";
    data.recent_activities.forEach((activity) => {
      const row = document.createElement("tr");
      row.innerHTML = `
                <td>${activity.user}</td>
                <td>${activity.time}</td>
                <td><span class="badge" style="background-color: ${activity.is_late ? "#dc3545" : "#28a745"};">${activity.status}</span></td>
            `;
      recentActivitiesBody.appendChild(row);
    });

    // Attendance Trend Chart
    const trendCtx = document
      .getElementById("attendanceTrend")
      .getContext("2d");
    if (attendanceChart) {
      attendanceChart.destroy();
    }
    attendanceChart = new Chart(trendCtx, {
      type: "line",
      data: {
        labels: data.attendance_trend.labels,
        datasets: [
          {
            label: "Present",
            data: data.attendance_trend.present,
            borderColor: "#28a745",
            fill: false,
          },
          {
            label: "Late",
            data: data.attendance_trend.late,
            borderColor: "#ffc107",
            fill: false,
          },
        ],
      },
    });

    // Department Breakdown Chart
    const deptCtx = document
      .getElementById("departmentBreakdown")
      .getContext("2d");
    if (departmentChart) {
      departmentChart.destroy();
    }
    departmentChart = new Chart(deptCtx, {
      type: "doughnut",
      data: {
        labels: data.department_breakdown.labels,
        datasets: [
          {
            data: data.department_breakdown.data,
            backgroundColor: [
              "#007bff",
              "#28a745",
              "#ffc107",
              "#dc3545",
              "#17a2b8",
            ],
          },
        ],
      },
    });
  };

  const applyFilter = () => {
    const startDate = document.getElementById("startDate").value;
    const endDate = document.getElementById("endDate").value;
    fetchData(startDate, endDate);
  };

  document.getElementById("applyFilter").addEventListener("click", applyFilter);

  document.getElementById("presetFilter").addEventListener("change", (e) => {
    const preset = e.target.value;
    const today = new Date();
    let start, end;

    switch (preset) {
      case "today":
        start = end = today.toISOString().split("T")[0];
        break;
      case "yesterday":
        const yesterday = new Date(today);
        yesterday.setDate(today.getDate() - 1);
        start = end = yesterday.toISOString().split("T")[0];
        break;
      case "last7":
        end = today.toISOString().split("T")[0];
        const last7 = new Date(today);
        last7.setDate(today.getDate() - 6);
        start = last7.toISOString().split("T")[0];
        break;
      case "last30":
        end = today.toISOString().split("T")[0];
        const last30 = new Date(today);
        last30.setDate(today.getDate() - 29);
        start = last30.toISOString().split("T")[0];
        break;
      case "thisMonth":
        end = today.toISOString().split("T")[0];
        start = new Date(today.getFullYear(), today.getMonth(), 1)
          .toISOString()
          .split("T")[0];
        break;
      case "lastMonth":
        const lastMonth = new Date(
          today.getFullYear(),
          today.getMonth() - 1,
          1,
        );
        start = lastMonth.toISOString().split("T")[0];
        end = new Date(today.getFullYear(), today.getMonth(), 0)
          .toISOString()
          .split("T")[0];
        break;
    }

    if (start && end) {
      document.getElementById("startDate").value = start;
      document.getElementById("endDate").value = end;
      fetchData(start, end);
    }
  });

  // Initial data fetch
  fetchData();
});
