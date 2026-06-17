(function () {
    const root = document.documentElement;
    const storedTheme = localStorage.getItem('professordash-theme');

    if (storedTheme) {
        root.setAttribute('data-theme', storedTheme);
    }

    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
        button.addEventListener('click', () => {
            const nextTheme = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            root.setAttribute('data-theme', nextTheme);
            localStorage.setItem('professordash-theme', nextTheme);
        });
    });

    if (window.lucide) {
        window.lucide.createIcons();
    }
}());
