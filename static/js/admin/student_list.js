function openStudentModalFromData(element) {
    // This grabs all the data-* fields cleanly from the button you clicked
    const id = element.getAttribute('data-id');
    const name = element.getAttribute('data-name');
    const course = element.getAttribute('data-course');
    const year = element.getAttribute('data-year');
    const email = element.getAttribute('data-email');
    const sessions = element.getAttribute('data-sessions');
    const points = element.getAttribute('data-points');
    const count = element.getAttribute('data-count');
    const active = element.getAttribute('data-active');
    const lab = element.getAttribute('data-lab');
    const subject = element.getAttribute('data-subject');

    // Forwards them cleanly to your original modal processing function
    openStudentModal(id, name, course, year, email, sessions, points, count, active, lab, subject);
}