# Concepts

Zendev is deliberately smaller than the policies built with it. Two boundaries
keep the toolkit reusable:

- [Repository-native development](repository-native.md) explains why durable
  state stays in committed, reviewable files.
- [Configuration ownership](configuration-ownership.md) separates shared
  validation mechanics from repository-specific meaning.

The same split appears throughout the product: Python packages own typed
mechanisms, thin hooks and Actions adapt those mechanisms to a host, and the
consuming repository owns its policy.
