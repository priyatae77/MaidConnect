window.onload = function(){
    setTimeout(() => {
        document.getElementById("loader").style.display = "none";
        document.getElementById("main-content").style.display = "block";
    }, 2000);
}
document.querySelectorAll(".book-btn").forEach(button => {
    button.addEventListener("click", function () {
        let workerId = this.getAttribute("data-id");
        bookWorker(workerId);
    });
});