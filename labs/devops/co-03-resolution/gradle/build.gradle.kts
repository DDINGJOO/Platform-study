// 소스는 maven/<모듈>/src 를 같이 쓴다. 빌드 도구만 다르고 코드와 그래프는 같다.
subprojects {
    repositories {
        maven { url = uri("file:///work/repo") }
        mavenCentral()
    }
    plugins.withType<JavaPlugin> {
        extensions.configure<JavaPluginExtension> {
            toolchain.languageVersion.set(JavaLanguageVersion.of(21))
            sourceSets.named("main") { java.setSrcDirs(listOf("../../maven/${project.name}/src/main/java")) }
        }
    }
}
