# Make Contribution

Meridian is built on top of the open-source [DeepTutor](https://github.com/HKUDS/DeepTutor)
engine (HKUDS, Apache 2.0). See [ATTRIBUTION.md](https://github.com/dhruvshah464/DeepTutor/blob/main/ATTRIBUTION.md)
for what is inherited versus original in this fork.

## Community

This fork does not run its own WeChat/Feishu/Discord channels. For questions
about the underlying tutoring engine, see the upstream DeepTutor community
channels linked from [Communication.md](https://github.com/HKUDS/DeepTutor/blob/dev/Communication.md).
For anything specific to Meridian, open an issue on
[this repository](https://github.com/dhruvshah464/DeepTutor/issues).

## We Welcome Contributions!

Whether you're fixing bugs, improving documentation, or adding new features, your contributions are valuable to us.

### How to Contribute

1. **Report Bugs** — Found a bug? Open an issue on GitHub with reproduction steps
2. **Suggest Features** — Share ideas in GitHub Discussions or our community channels
3. **Improve Docs** — Help us improve documentation, tutorials, and examples
4. **Submit Code** — Fix bugs or implement new features through pull requests

### Contribution Guidelines

For detailed guidelines, see [CONTRIBUTING.md](https://github.com/dhruvshah464/DeepTutor/blob/main/CONTRIBUTING.md).

**Key Points:**

- All contributions must be based on the `dev` branch
- Run `pre-commit run --all-files` before submitting
- Use conventional commit format: `feat:`, `fix:`, `docs:`, etc.

### Quick Start

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/DeepTutor.git
cd DeepTutor

# Create feature branch from dev
git checkout dev && git pull origin dev
git checkout -b feature/your-feature-name

# Install pre-commit hooks
pip install pre-commit && pre-commit install

# Make changes, then submit PR to dev branch
```

## Contributors

<a href="https://github.com/dhruvshah464/DeepTutor/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=dhruvshah464/DeepTutor&max=999" alt="Contributors" />
</a>

This fork's own contributor graph is above. Full credit for the underlying
engine goes to the [upstream DeepTutor contributors](https://github.com/HKUDS/DeepTutor/graphs/contributors).

---

Thank you for your interest in contributing! 🚀

<style>
.community-links {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin: 20px 0;
}

.community-badge {
  display: inline-flex;
  align-items: center;
  padding: 10px 18px;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.95rem;
  text-decoration: none;
  transition: all 0.2s ease;
}

.community-badge:hover {
  transform: translateY(-2px);
}

.community-badge.wechat {
  background: #07C160;
  color: white;
}

.community-badge.wechat-collab {
  background: #1AAD19;
  color: white;
}

.community-badge.discord {
  background: #5865F2;
  color: white;
}
</style>
