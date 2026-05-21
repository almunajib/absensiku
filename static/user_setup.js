document.addEventListener("DOMContentLoaded", () => {
  const userForm = document.getElementById("user-form");
  const addUserBtn = document.getElementById("add-user-btn");
  const updateUserBtn = document.getElementById("update-user-btn");
  const clearFormBtn = document.getElementById("clear-form-btn");
  const userTableBody = document.querySelector("#user-table tbody");

  const API_URL = "/api/users";
  const DEPARTMENTS_API_URL = "/api/departments";

  let departments = [];

  // Function to fetch departments and populate the dropdown
  const fetchDepartments = async () => {
    try {
      const response = await fetch(DEPARTMENTS_API_URL);
      departments = await response.json();
      const groupDropdown = document.getElementById("group_id");
      groupDropdown.innerHTML = ""; // Clear existing options
      departments.forEach((dept) => {
        const option = document.createElement("option");
        option.value = dept.deptid;
        option.textContent = `ID: ${dept.deptid} (${dept.deptname})`;
        groupDropdown.appendChild(option);
      });
    } catch (error) {
      console.error("Error fetching departments:", error);
    }
  };

  // Function to fetch users and populate the table
  const fetchUsers = async () => {
    try {
      const response = await fetch(API_URL);
      const users = await response.json();
      userTableBody.innerHTML = ""; // Clear existing rows
      users.forEach((user) => {
        const row = document.createElement("tr");
        row.innerHTML = `
                    <td>${user.user_id}</td>
                    <td>${user.name}</td>
                    <td>${user.privilege == 14 ? "Administrator" : "User"}</td>
                    <td>${user.group_id || ""}</td>
                    <td>${user.card}</td>
                    <td class="actions">
                        <button class="edit-btn" data-uid="${user.uid}" data-userid="${user.user_id}">Edit</button>
                        <button class="delete-btn" data-userid="${user.user_id}">Delete</button>
                    </td>
                `;
        userTableBody.appendChild(row);
      });
    } catch (error) {
      console.error("Error fetching users:", error);
    }
  };

  // Function to handle form submission for adding a user
  const addUser = async (e) => {
    e.preventDefault();
    const formData = new FormData(userForm);
    const data = Object.fromEntries(formData.entries());

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (response.ok) {
        fetchUsers();
        userForm.reset();
      } else {
        const result = await response.json();
        alert(`Error: ${result.message}`);
      }
    } catch (error) {
      console.error("Error adding user:", error);
    }
  };

  // Function to handle updating a user
  const updateUser = async () => {
    const formData = new FormData(userForm);
    const data = Object.fromEntries(formData.entries());
    const userId = document.getElementById("user_id").value; // Get user_id from disabled input

    try {
      const response = await fetch(`${API_URL}/${userId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (response.ok) {
        fetchUsers();
        resetForm();
      } else {
        const result = await response.json();
        alert(`Error: ${result.message}`);
      }
    } catch (error) {
      console.error("Error updating user:", error);
    }
  };

  // Function to handle deleting a user
  const deleteUser = async (userId) => {
    if (!confirm(`Are you sure you want to delete user ${userId}?`)) {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/${userId}`, {
        method: "DELETE",
      });

      if (response.ok) {
        fetchUsers();
      } else {
        const result = await response.json();
        alert(`Error: ${result.message}`);
      }
    } catch (error) {
      console.error("Error deleting user:", error);
    }
  };

  const populateFormForEdit = async (userId) => {
    try {
      const response = await fetch(`${API_URL}/${userId}`);
      const user = await response.json();

      document.getElementById("uid").value = user.uid;
      document.getElementById("user_id").value = user.user_id;
      document.getElementById("user_id").disabled = true; // Disable user_id field
      document.getElementById("name").value = user.name;
      document.getElementById("privilege").value = user.privilege;
      // Password is not shown for security reasons.
      // Entering a new password will update it, leaving it blank will keep the old one.
      document.getElementById("password").value = "";

      // Find the department in the dropdown and select it
      const groupDropdown = document.getElementById("group_id");
      const dept = departments.find((d) => d.deptname === user.group_id);
      if (dept) {
        groupDropdown.value = dept.deptid;
      }

      document.getElementById("card").value = user.card;

      addUserBtn.style.display = "none";
      updateUserBtn.style.display = "inline-block";
    } catch (error) {
      console.error("Error fetching user data for edit:", error);
    }
  };

  // Function to reset the form
  const resetForm = () => {
    userForm.reset();
    document.getElementById("uid").value = "";
    document.getElementById("user_id").disabled = false; // Re-enable user_id field
    addUserBtn.style.display = "inline-block";
    updateUserBtn.style.display = "none";
  };
  // Event Listeners
  userForm.addEventListener("submit", addUser);
  updateUserBtn.addEventListener("click", updateUser);
  clearFormBtn.addEventListener("click", resetForm);

  userTableBody.addEventListener("click", (e) => {
    if (e.target.classList.contains("edit-btn")) {
      const userId = e.target.dataset.userid;
      populateFormForEdit(userId);
    }

    if (e.target.classList.contains("delete-btn")) {
      const userId = e.target.dataset.userid;
      deleteUser(userId);
    }
  });

  // Initial fetch
  const init = async () => {
    await fetchDepartments();
    await fetchUsers();
  };

  init();
});
