document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelectorAll('.tab-link');
    const contents = document.querySelectorAll('.tab-content');
    const novelTitleHeader = document.getElementById('novelTitleHeader');
    const novelDetailTitle = document.getElementById('novelDetailTitle');

    // Function to get novel title from URL query parameter (example)
    function getNovelTitle() {
        const params = new URLSearchParams(window.location.search);
        return params.get('title') || '小说详情'; // Default title
    }

    const currentNovelTitle = getNovelTitle();
    if (novelTitleHeader) novelTitleHeader.textContent = currentNovelTitle;
    if (novelDetailTitle) novelDetailTitle.textContent = currentNovelTitle;
    document.title = `小说详情 - ${currentNovelTitle}`;


    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Deactivate all tabs and content
            tabs.forEach(t => t.classList.remove('active'));
            contents.forEach(c => c.classList.remove('active'));

            // Activate clicked tab and corresponding content
            tab.classList.add('active');
            const targetContentId = tab.getAttribute('data-tab');
            const targetContent = document.getElementById(targetContentId); // Added to get element
            if (targetContent) targetContent.classList.add('active'); // Check if element exists
        });
    });

    // Character view toggle
    const charListViewBtn = document.getElementById('charListViewBtn');
    const charGraphViewBtn = document.getElementById('charGraphViewBtn');
    const characterListView = document.getElementById('characterListView');
    const characterGraphView = document.getElementById('characterGraphView');

    if (charListViewBtn && charGraphViewBtn && characterListView && characterGraphView) {
        charListViewBtn.addEventListener('click', () => {
            characterListView.style.display = 'block';
            characterGraphView.style.display = 'none';
            charListViewBtn.classList.add('active');
            charGraphViewBtn.classList.remove('active');
        });

        charGraphViewBtn.addEventListener('click', () => {
            characterListView.style.display = 'none';
            characterGraphView.style.display = 'block';
            charGraphViewBtn.classList.add('active');
            charListViewBtn.classList.remove('active');
        });
    }

    // Chapter list item click
    const chapterListItems = document.querySelectorAll('.chapter-list-item');
    const chapterTitleDisplay = document.getElementById('chapterTitle');
    const chapterContentView = document.getElementById('chapterContentView');

    chapterListItems.forEach(item => {
        item.addEventListener('click', () => {
            chapterListItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');

            const chapterId = item.getAttribute('data-chapter-id');
            // In a real app, fetch chapter content based on chapterId
            if (chapterTitleDisplay) chapterTitleDisplay.textContent = item.textContent;
            if (chapterContentView) chapterContentView.innerHTML = `<p>正在加载章节 ${chapterId} (${item.textContent})...</p><p>示例内容：这是章节 ${item.textContent} 的详细内容。魔法森林深处的秘密即将揭晓。</p>`;
        });
    });

    // Activate the first tab by default if no hash
    // Ensure this runs after other event listeners are set up and content is ready.
    const activateInitialTab = () => {
        // Check if a tab is already active from HTML (e.g. class="active" in the HTML itself)
        const activeTabInHTML = document.querySelector('.tab-link.active');
        const activeContentInHTML = document.querySelector('.tab-content.active');

        if (activeTabInHTML && activeContentInHTML) {
            // If HTML already defines an active tab and content, ensure JS reflects this
            // by making sure no other tab/content thinks it's active.
            tabs.forEach(t => { if (t !== activeTabInHTML) t.classList.remove('active'); });
            contents.forEach(c => { if (c !== activeContentInHTML) c.classList.remove('active'); });
            // Ensure the content for the HTML-active tab is indeed displayed
            if (!activeContentInHTML.classList.contains('active')) {
                 activeContentInHTML.classList.add('active');
            }
            return; // HTML default active tab is set
        }

        // If no tab is active via HTML, click the first tab.
        const firstTab = document.querySelector('.tab-link');
        if (firstTab) {
            firstTab.click();
        }
    };

    const activateTabFromHash = () => {
        const hash = window.location.hash.substring(1); // remove #
        let tabActivatedByHash = false;
        if (hash) {
            const targetTab = document.querySelector(`.tab-link[data-tab="${hash}"]`);
            if (targetTab) {
                // Deactivate all first, then activate the target
                tabs.forEach(t => t.classList.remove('active'));
                contents.forEach(c => c.classList.remove('active'));
                targetTab.click(); // This will handle making it active and showing content
                tabActivatedByHash = true;
            }
        }
        return tabActivatedByHash;
    };

    if (!activateTabFromHash()) {
        activateInitialTab();
    }

    window.addEventListener('hashchange', activateTabFromHash);

});
