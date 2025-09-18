document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    try {
        const response = await fetch("http://127.0.0.1:8000/login", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({
                username: username,
                password: password
            })
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem("token", data.access_token); // save token
            window.location.href = "dashboard.html"; // redirect
        } else {
            document.getElementById("error-message").classList.remove("hidden");
        }
    } catch (err) {
        console.error("Error logging in:", err);
        document.getElementById("error-message").classList.remove("hidden");
    }
});

async function searchLeads() {
  const token = localStorage.getItem("token"); // grab saved token
  const industry = document.getElementById("industry").value;
  const location = document.getElementById("location").value;

  const response = await fetch(`http://127.0.0.1:8000/leadsearch?industry=${industry}&location=${location}`, {
    headers: { "Authorization": `Bearer ${token}` }
  });

  const data = await response.json();
  console.log(data.results); // render this into table
};


//dashboard code

   // Drawer functionality
        const leadgenCard = document.getElementById('leadgen-card');
        const drawerOverlay = document.getElementById('drawer-overlay');
        const drawerPanel = document.getElementById('drawer-panel');
        const closeDrawer = document.getElementById('close-drawer');
        const leadgenForm = document.getElementById('leadgen-form');
        const resultsSection = document.getElementById('results-section');
        const resultsTbody = document.getElementById('results-tbody');

        // Open drawer
        leadgenCard.addEventListener('click', () => {
            drawerOverlay.classList.remove('hidden');
            setTimeout(() => {
                drawerPanel.classList.remove('drawer-enter');
                drawerPanel.classList.add('drawer-enter-active');
            }, 10);
        });

        // Close drawer
        function closeDrawerPanel() {
            drawerPanel.classList.remove('drawer-enter-active');
            drawerPanel.classList.add('drawer-exit-active');
            setTimeout(() => {
                drawerOverlay.classList.add('hidden');
                drawerPanel.classList.remove('drawer-exit-active');
                drawerPanel.classList.add('drawer-enter');
            }, 300);
        }

        closeDrawer.addEventListener('click', closeDrawerPanel);
        drawerOverlay.addEventListener('click', (e) => {
            if (e.target === drawerOverlay) {
                closeDrawerPanel();
            }
        });

        // Form submission
        leadgenForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            const formData = new FormData(leadgenForm);
            const industry = formData.get('industry');
            const location = formData.get('location');
            const role = formData.get('role');
            const limit = parseInt(formData.get('limit'));

            // Generate sample results
            const sampleResults = generateSampleLeads(industry, location, role, limit);
            
            // Display results
            displayResults(sampleResults);
        });

        function generateSampleLeads(industry, location, role, limit) {
            const firstNames = ['John', 'Sarah', 'Michael', 'Emily', 'David', 'Jessica', 'Robert', 'Ashley', 'James', 'Amanda'];
            const lastNames = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez'];
            const roles = role ? [role] : ['CEO', 'CTO', 'Marketing Manager', 'Sales Director', 'VP of Engineering', 'Product Manager'];
            const companies = [`${industry} Corp`, `${location} ${industry}`, `Global ${industry} Solutions`, `${industry} Innovations`, `${location} Tech`];

            const results = [];
            for (let i = 0; i < limit; i++) {
                const firstName = firstNames[Math.floor(Math.random() * firstNames.length)];
                const lastName = lastNames[Math.floor(Math.random() * lastNames.length)];
                const personRole = roles[Math.floor(Math.random() * roles.length)];
                const company = companies[Math.floor(Math.random() * companies.length)];
                
                results.push({
                    firstName,
                    lastName,
                    role: personRole,
                    company,
                    profileUrl: `https://linkedin.com/in/${firstName.toLowerCase()}-${lastName.toLowerCase()}`
                });
            }
            return results;
        }

        function displayResults(results) {
            resultsTbody.innerHTML = '';
            
            results.forEach(lead => {
                const row = document.createElement('tr');
                row.className = 'hover:bg-gray-50';
                row.innerHTML = `
                    <td class="px-4 py-3 text-sm text-gray-900">${lead.firstName}</td>
                    <td class="px-4 py-3 text-sm text-gray-900">${lead.lastName}</td>
                    <td class="px-4 py-3 text-sm text-gray-600">${lead.role}</td>
                    <td class="px-4 py-3 text-sm text-gray-600">${lead.company}</td>
                    <td class="px-4 py-3 text-sm">
                        <a href="${lead.profileUrl}" target="_blank" class="text-blue-600 hover:text-blue-800 underline">
                            View Profile
                        </a>
                    </td>
                `;
                resultsTbody.appendChild(row);
            });

            resultsSection.classList.remove('hidden');
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !drawerOverlay.classList.contains('hidden')) {
                closeDrawerPanel();
            }
        });


        document.getElementById("leadgen-form").addEventListener("submit", async (e) => {
    e.preventDefault(); // stop page reload

    // 1. Grab values from inputs
    const industry = document.getElementById("industry").value;
    const location = document.getElementById("location").value;
    const role = document.getElementById("role").value;
    const limit = document.getElementById("limit").value;

    // 2. Grab token from localStorage
    const token = localStorage.getItem("token");

    // 3. Call backend
    const response = await fetch(`http://127.0.0.1:8000/leadsearch?industry=${industry}&location=${location}&role_hint=${role}&limit=${limit}`, {
        headers: { "Authorization": `Bearer ${token}` }
    });

    const data = await response.json();

    // 4. Render results in table
    renderResults(data.results);
});

function renderResults(results) {
    const tbody = document.getElementById("results-tbody");
    tbody.innerHTML = ""; // clear old results

    results.forEach(lead => {
        const row = document.createElement("tr");

        row.innerHTML = `
            <td class="px-4 py-3">${lead.first_name || ""}</td>
            <td class="px-4 py-3">${lead.last_name || ""}</td>
            <td class="px-4 py-3">${lead.role || ""}</td>
            <td class="px-4 py-3">${lead.company || ""}</td>
            <td class="px-4 py-3">
                <a href="${lead.profile_url}" target="_blank" class="text-blue-600 hover:underline">Profile</a>
            </td>
        `;

        tbody.appendChild(row);
    });

    // Show results section if hidden
    document.getElementById("results-section").classList.remove("hidden");
}