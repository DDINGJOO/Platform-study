package lab.lookup;

import com.google.crypto.tink.DeterministicAead;
import com.google.crypto.tink.InsecureSecretKeyAccess;
import com.google.crypto.tink.KeysetHandle;
import com.google.crypto.tink.RegistryConfiguration;
import com.google.crypto.tink.TinkJsonProtoKeysetFormat;
import com.google.crypto.tink.daead.DeterministicAeadConfig;
import com.google.crypto.tink.daead.PredefinedDeterministicAeadParameters;

import java.nio.file.Files;
import java.nio.file.Path;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.Properties;

/**
 * 실습용 키 묶음. 운영 키가 아니다. seed 가 새로 만들어 out/lab-keys.properties 에 평문으로 저장하고
 * (그래서 out/ 은 커밋하지 않는다) 이후 실행이 같은 키를 읽는다.
 *
 * - det    : Tink 결정적 AEAD(AES256_SIV) 키셋. 회전하면 키가 둘이 된다
 * - gcmKey : AES-256-GCM 키. 암호문 첫 바이트가 키 번호(gcmKeyId)
 * - idxKey : 블라인드 인덱스용 HMAC-SHA256 키. 암호화 키와 따로 둔다
 */
public final class LabKeys {
    static volatile KeysetHandle det;
    static volatile DeterministicAead detPrimitive;
    static volatile byte[] gcmKey;
    static volatile byte gcmKeyId = 1;
    static volatile byte[] oldGcmKey;      // 회전 중에만 쓴다
    static volatile byte[] idxKey;

    private static final Path FILE = Path.of("out/lab-keys.properties");

    static {
        try { DeterministicAeadConfig.register(); } catch (Exception e) { throw new IllegalStateException(e); }
    }

    static void init() {}   // 정적 초기화(Tink 등록)만 일으킨다

    static void generateAndSave() throws Exception {
        SecureRandom r = new SecureRandom();
        setDet(KeysetHandle.generateNew(PredefinedDeterministicAeadParameters.AES256_SIV));
        gcmKey = new byte[32]; r.nextBytes(gcmKey);
        idxKey = new byte[32]; r.nextBytes(idxKey);
        gcmKeyId = 1;
        save();
    }

    static void save() throws Exception {
        Properties p = new Properties();
        p.setProperty("det", TinkJsonProtoKeysetFormat.serializeKeyset(det, InsecureSecretKeyAccess.get()));
        p.setProperty("gcm", Base64.getEncoder().encodeToString(gcmKey));
        p.setProperty("gcmKeyId", Byte.toString(gcmKeyId));
        p.setProperty("idx", Base64.getEncoder().encodeToString(idxKey));
        Files.createDirectories(FILE.getParent());
        try (var w = Files.newBufferedWriter(FILE)) { p.store(w, "LAB ONLY - throwaway keys for pii-06"); }
    }

    static void load() throws Exception {
        Properties p = new Properties();
        try (var rd = Files.newBufferedReader(FILE)) { p.load(rd); }
        setDet(TinkJsonProtoKeysetFormat.parseKeyset(p.getProperty("det"), InsecureSecretKeyAccess.get()));
        gcmKey = Base64.getDecoder().decode(p.getProperty("gcm"));
        gcmKeyId = Byte.parseByte(p.getProperty("gcmKeyId"));
        idxKey = Base64.getDecoder().decode(p.getProperty("idx"));
    }

    static void setDet(KeysetHandle h) throws Exception {
        det = h;
        detPrimitive = h.getPrimitive(RegistryConfiguration.get(), DeterministicAead.class);
    }

    private LabKeys() {}
}
