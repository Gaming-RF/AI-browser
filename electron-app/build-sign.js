exports.default = async function(configuration) {
  // Skipping code signing to bypass winCodeSign symlink errors on Windows without Developer Mode
  console.log("Skipping code signing for " + configuration.path);
};
