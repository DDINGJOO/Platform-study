window.spinnakerSettings.gateUrl = 'http://localhost:28101';
window.spinnakerSettings.authEnabled = false;
window.spinnakerSettings.authEndpoint = 'http://localhost:28101/auth/user';
window.spinnakerSettings.defaultProviders = [];
window.spinnakerSettings.feature = window.spinnakerSettings.feature || {};
window.spinnakerSettings.feature.canary = true;
window.spinnakerSettings.feature.managedPipelineTemplatesV2UI = false;
window.spinnakerSettings.canary = {
  enabled: true,
  featureDisabled: false,
  optInAll: true,
  metricsAccountName: 'prometheus',
  metricStore: 'prometheus',
  storageAccountName: 'memory',
  manualAnalysisEnabled: true,
  stagesEnabled: true,
  reduxLogger: false,
  defaultJudge: 'NetflixACAJudge-v1.0',
  defaultMetricsAccount: 'prometheus',
  defaultStorageAccount: 'memory',
  defaultConfigurationAccount: 'memory',
  defaultMetricsStore: 'prometheus',
  showAllConfigs: true,
  templatesEnabled: true
};
