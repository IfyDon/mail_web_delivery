// Alpine component: hero code-block copy button
function heroCopy() {
  var code = 'curl -X POST https://api.webmail.io/v1/send \\\n' +
    '  -H "Authorization: Bearer <api_key>" \\\n' +
    '  -H "Content-Type: application/json" \\\n' +
    '  -d \'{\n' +
    '    "to":        "user@example.com",\n' +
    '    "from":      "you@yourdomain.com",\n' +
    '    "subject":   "Welcome",\n' +
    '    "html_body": "<h1>Hello!</h1>"\n' +
    '  }\'';
  return {
    copied: false,
    copy: function() {
      var self = this;
      if (navigator.clipboard) {
        navigator.clipboard.writeText(code).then(function() {
          self.copied = true;
          setTimeout(function() { self.copied = false; }, 2000);
        });
      }
    },
  };
}

// Alpine component: stats bar entrance animation
function statsBar() {
  return {
    init: function(el) {
      var io = new IntersectionObserver(function(entries) {
        var entry = entries[0];
        if (entry.isIntersecting) {
          el.querySelectorAll('.stat-num').forEach(function(n, i) {
            n.style.animationDelay = (i * 0.12) + 's';
            n.style.animationFillMode = 'both';
          });
          io.disconnect();
        }
      }, { threshold: 0.4 });
      io.observe(el);
    },
  };
}

// Alpine component: testimonials carousel
function testimonials() {
  return {
    active: 0,
    total: 3,
    next: function() { this.active = (this.active + 1) % this.total; },
    prev: function() { this.active = (this.active - 1 + this.total) % this.total; },
  };
}

// Alpine component: code integration tabs
function codeTabs() {
  return {
    active: 0,
    copied: false,
    tabs: [
      {
        label: 'cURL',
        lang: 'bash',
        code: 'curl -X POST https://api.webmail.io/api/v1/send \\\n' +
          '  -H "Authorization: Bearer sk_live_your_key" \\\n' +
          '  -H "Content-Type: application/json" \\\n' +
          '  -d \'{\n' +
          '    "from": "hello@yourdomain.com",\n' +
          '    "to":   "user@example.com",\n' +
          '    "subject": "Welcome to WebMail",\n' +
          '    "html_body": "<h1>Hello!</h1><p>Thanks for signing up.</p>",\n' +
          '    "stream": "transactional"\n' +
          '  }\'',
      },
      {
        label: 'Python',
        lang: 'python',
        code: 'import requests\n\n' +
          'response = requests.post(\n' +
          '    "https://api.webmail.io/api/v1/send",\n' +
          '    headers={"Authorization": "Bearer sk_live_your_key"},\n' +
          '    json={\n' +
          '        "from":     "hello@yourdomain.com",\n' +
          '        "to":       "user@example.com",\n' +
          '        "subject":  "Welcome to WebMail",\n' +
          '        "html_body": "<h1>Hello!</h1>",\n' +
          '        "stream":   "transactional",\n' +
          '    },\n' +
          ')\n' +
          'print(response.json())\n' +
          "# {'message_id': '550e8400-...', 'status': 'queued'}",
      },
      {
        label: 'Node.js',
        lang: 'javascript',
        code: 'const res = await fetch("https://api.webmail.io/api/v1/send", {\n' +
          '  method: "POST",\n' +
          '  headers: {\n' +
          '    "Authorization": "Bearer sk_live_your_key",\n' +
          '    "Content-Type": "application/json",\n' +
          '  },\n' +
          '  body: JSON.stringify({\n' +
          '    from:      "hello@yourdomain.com",\n' +
          '    to:        "user@example.com",\n' +
          '    subject:   "Welcome to WebMail",\n' +
          '    html_body: "<h1>Hello!</h1>",\n' +
          '    stream:    "transactional",\n' +
          '  }),\n' +
          '});\n' +
          'const data = await res.json();\n' +
          'console.log(data.message_id);',
      },
      {
        label: 'Ruby',
        lang: 'ruby',
        code: 'require "net/http"\n' +
          'require "json"\n\n' +
          'uri  = URI("https://api.webmail.io/api/v1/send")\n' +
          'http = Net::HTTP.new(uri.host, uri.port)\n' +
          'http.use_ssl = true\n\n' +
          'req = Net::HTTP::Post.new(uri)\n' +
          'req["Authorization"] = "Bearer sk_live_your_key"\n' +
          'req["Content-Type"]  = "application/json"\n' +
          'req.body = JSON.dump(\n' +
          '  from: "hello@yourdomain.com", to: "user@example.com",\n' +
          '  subject: "Welcome", html_body: "<h1>Hello!</h1>",\n' +
          '  stream: "transactional"\n' +
          ')\n\n' +
          'puts JSON.parse(http.request(req).body)["message_id"]',
      },
      {
        label: '.NET',
        lang: 'csharp',
        code: 'using var client = new HttpClient();\n' +
          'client.DefaultRequestHeaders\n' +
          '      .Add("Authorization", "Bearer sk_live_your_key");\n\n' +
          'var payload = new {\n' +
          '    from      = "hello@yourdomain.com",\n' +
          '    to        = "user@example.com",\n' +
          '    subject   = "Welcome to WebMail",\n' +
          '    html_body = "<h1>Hello!</h1>",\n' +
          '    stream    = "transactional",\n' +
          '};\n\n' +
          'var response = await client.PostAsJsonAsync(\n' +
          '    "https://api.webmail.io/api/v1/send", payload);\n' +
          'var data = await response.Content.ReadFromJsonAsync<JsonElement>();\n' +
          'Console.WriteLine(data.GetProperty("message_id"));',
      },
      {
        label: 'PHP',
        lang: 'php',
        code: '<?php\n' +
          '$ch = curl_init("https://api.webmail.io/api/v1/send");\n' +
          'curl_setopt_array($ch, [\n' +
          '    CURLOPT_POST           => true,\n' +
          '    CURLOPT_RETURNTRANSFER => true,\n' +
          '    CURLOPT_HTTPHEADER     => [\n' +
          '        "Authorization: Bearer sk_live_your_key",\n' +
          '        "Content-Type: application/json",\n' +
          '    ],\n' +
          '    CURLOPT_POSTFIELDS => json_encode([\n' +
          '        "from"      => "hello@yourdomain.com",\n' +
          '        "to"        => "user@example.com",\n' +
          '        "subject"   => "Welcome to WebMail",\n' +
          '        "html_body" => "<h1>Hello!</h1>",\n' +
          '        "stream"    => "transactional",\n' +
          '    ]),\n' +
          ']);\n' +
          '$data = json_decode(curl_exec($ch), true);\n' +
          'echo $data["message_id"];',
      },
    ],
    copy: function() {
      var self = this;
      if (navigator.clipboard) {
        navigator.clipboard.writeText(this.tabs[this.active].code).then(function() {
          self.copied = true;
          setTimeout(function() { self.copied = false; }, 2000);
        });
      }
    },
  };
}

// Scroll reveal via IntersectionObserver
(function() {
  var io = new IntersectionObserver(function(entries) {
    entries.forEach(function(e) {
      if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
    });
  }, { threshold: 0.12 });
  document.querySelectorAll('[data-reveal]').forEach(function(el) { io.observe(el); });
})();
