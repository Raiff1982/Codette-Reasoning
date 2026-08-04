import { Client } from "@gradio/client";

function log_status(status) {
	console.log(
		`The current status for this job is: ${JSON.stringify(status, null, 2)}.`
	);
}

const app = await Client.connect("abidlabs/en2fr", {
	events: ["status", "data"]
});
const job = app.submit("/predict", ["Hello"]);

for await (const message of job) {
	if (message.type === "status") {
		log_status(message);
	}
}