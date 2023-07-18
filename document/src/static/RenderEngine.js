class RenderEngine extends HTMLElement {
  connectedCallback() {
    // Parse the example JSON document
    this.exampleJson = JSON.parse(this.getAttribute('json'));
    
    // Get the target URL
    this.target = this.getAttribute('target');

    // Render the initial state
    this.innerHTML = `
      <div style="display: flex; flex-direction: column; justify-content: space-between;">
        <div id="preview-area"></div>
        <textarea id="template" rows="10" cols="50">{{title}}\n{{abstract}}</textarea>
        <button id="submit">Submit</button>
      </div>
    `;

    // Add event listeners
    this.querySelector('#submit').addEventListener('click', () => this.submit());
  }

  preview(innerHTML) {
    // Get the user's template
    let template = this.querySelector('#template').value;

    // Display the rendered output in the preview area
    this.querySelector('#preview-area').innerHTML = innerHTML;
  }

  submit() {
    // Get the user's template
    let template = this.querySelector('#template').value;

    // Post the user's template to the target URL
    fetch(this.target, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({template: template, json: this.exampleJson})
    })
    .then(response => response.json())
    .then(data => {
      console.log("success!", data);
      this.preview(data.html);
    })
    .catch((error) => {
      console.error('Error:', error);
    });
  }
}

window.customElements.define('render-engine', RenderEngine);
