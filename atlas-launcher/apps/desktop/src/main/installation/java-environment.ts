/** Keep OS essentials, never inherit API keys or JVM option injection from the launcher environment. */
export function javaEnvironment(source: NodeJS.ProcessEnv, javaHome: string): NodeJS.ProcessEnv {
  const allowed = new Set([
    'PATH',
    'SYSTEMROOT',
    'SYSTEMDRIVE',
    'WINDIR',
    'TEMP',
    'TMP',
    'USERPROFILE',
    'APPDATA',
    'LOCALAPPDATA',
    'USERNAME',
    'USERDOMAIN',
    'PROGRAMDATA',
    'PROGRAMFILES',
    'PROGRAMFILES(X86)',
    'PROGRAMW6432',
    'PUBLIC',
    'NUMBER_OF_PROCESSORS',
    'PROCESSOR_ARCHITECTURE',
    'COMSPEC',
    'LANG',
    'LC_ALL',
    'LC_CTYPE',
  ]);
  const output: NodeJS.ProcessEnv = {};
  for (const [key, value] of Object.entries(source))
    if (allowed.has(key.toUpperCase()) && value !== undefined) output[key] = value;
  output.JAVA_HOME = javaHome;
  return output;
}
