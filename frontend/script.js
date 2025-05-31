document.addEventListener('DOMContentLoaded', () => {
    const mainContent = document.querySelector('.main');
    const navLinks = document.querySelectorAll('.nav-link');
    const modal = document.getElementById('modal');
    const modalCloseBtn = document.querySelector('.modal-close');
    const notifications = document.getElementById('notifications');

    // Function to load and display a section
    async function loadSection(sectionId, pushState = true) {
        // Remove 'active' class from all sections (if any were loaded directly)
        // and remove 'active' class from all nav links
        navLinks.forEach(link => link.classList.remove('active'));
        // document.querySelectorAll('.main .section').forEach(sec => sec.classList.remove('active'));
        // The above line is commented out as sections are now replaced, not just hidden/shown

        // Construct file name (e.g., 'home.html')
        const fileName = `${sectionId}.html`;

        try {
            const response = await fetch(fileName);
            if (!response.ok) {
                console.error(`Error loading section ${sectionId}: ${response.statusText}`);
                mainContent.innerHTML = `<p>Error loading content for ${sectionId}. Please check if '${fileName}' exists in the 'frontend' directory.</p>`;
                return;
            }
            const html = await response.text();
            mainContent.innerHTML = html;

            // Add 'active' class to the current nav link
            const activeLink = document.querySelector(`.nav-link[data-section="${sectionId}"]`);
            if (activeLink) {
                activeLink.classList.add('active');
            }

            // If the loaded content has elements that need event listeners, re-attach them here.
            // For example, if generate.html has its own script logic or buttons.
            // This example keeps it simple. The original script's specific event listeners for
            // forms, buttons within sections will need to be re-evaluated or attached here.
            // For now, global functions like showSection (if called from within loaded HTML)
            // will need to be exposed or handled differently.

            if (pushState) {
               history.pushState({ section: sectionId }, '', `#${sectionId}`);
            }

        } catch (error) {
            console.error(`Error fetching section ${sectionId}:`, error);
            mainContent.innerHTML = `<p>Error loading content for ${sectionId}. Exception: ${error.message}</p>`;
        }
    }

    // Event listeners for navigation links
    navLinks.forEach(link => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            const sectionId = link.getAttribute('data-section');
            loadSection(sectionId);
        });
    });

    // Handle browser back/forward navigation
    window.addEventListener('popstate', (event) => {
        if (event.state && event.state.section) {
            loadSection(event.state.section, false);
        } else {
            // Default to home if no state or if hash is empty
            const hashSection = window.location.hash.substring(1);
            const validSectionsPop = ['home', 'generate', 'projects', 'settings'];
            if (hashSection && validSectionsPop.includes(hashSection)) {
                 loadSection(hashSection, false);
            } else {
                 loadSection('home', false);
            }
        }
    });
    
    // Initial section load based on URL hash or default to 'home'
    let initialSection = window.location.hash.substring(1) || 'home';
    // Validate initialSection to prevent loading arbitrary files
    const validSections = ['home', 'generate', 'projects', 'settings'];
    if (!validSections.includes(initialSection)) {
        initialSection = 'home';
    }
    loadSection(initialSection, false); // Load initial section without pushing state

    // --- Keep existing modal and notification logic (simplified) ---
    window.closeModal = function() {
        if (modal) modal.style.display = 'none';
    }
    if (modalCloseBtn) {
        modalCloseBtn.onclick = () => closeModal(); // Corrected to call closeModal
    }
    window.onclick = function(event) {
        if (event.target == modal) {
            closeModal();
        }
    }
    window.showNotification = function(message, type = 'info') {
         // Simplified notification logic
         const notification = document.createElement('div');
         notification.className = `notification ${type}`;
         notification.textContent = message;
         if (notifications) {
            notifications.appendChild(notification);
            setTimeout(() => notification.remove(), 3000);
         } else {
            console.warn("Notifications container not found. Could not display notification:", message);
         }
    }
    // --- End of existing modal and notification logic ---


    // Expose showSection globally if it's called from inline HTML attributes
    // like the "开始创作" button on home.html
    // A better approach would be to add event listeners after loading content.
    window.showSection = function(sectionId) {
        loadSection(sectionId);
    }
});