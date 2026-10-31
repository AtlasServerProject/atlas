import { readFile } from 'node:fs/promises';
import { NtExecutable, NtExecutableResource, Resource, Data } from 'resedit';
export async function checkInstallerIcon(executable, icon) {
  const resources = NtExecutableResource.from(NtExecutable.from(await readFile(executable)));
  const expected = Data.IconFile.from(await readFile(icon)).icons.map((x) => x.data);
  const bytes = (x) => Buffer.from(x.bin ?? x.generate());
  const groups = Resource.IconGroupEntry.fromEntries(resources.entries);
  if (
    !groups.slice(0, 1).some((group) => {
      const actual = group.getIconItemsFromEntries(resources.entries);
      return (
        actual.length === expected.length &&
        actual.every((x) =>
          expected.some(
            (y) =>
              (x.width || 256) === (y.width || 256) &&
              (x.height || 256) === (y.height || 256) &&
              bytes(x).equals(bytes(y)),
          ),
        )
      );
    })
  )
    throw Error('Installer icon does not match the Atlas ICO.');
  console.log(`Installer icon verified: all ${expected.length} Atlas sizes match.`);
}
