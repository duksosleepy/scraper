const button = document.querySelector("button");

button.addEventListener("click", (event) => {
	button.textContent = `Click count: ${event.detail}`;
});
