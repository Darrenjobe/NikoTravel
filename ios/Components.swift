import SwiftUI

struct MessageBubble: View {
    let message: ChatMessage
    let onShowMap: ([Place]) -> Void
    var accent: Color = .hodAegean

    private var isUser: Bool { message.role == .user }

    @ViewBuilder
    private var renderedText: some View {
        if let attr = try? AttributedString(
            markdown: message.text,
            options: .init(interpretedSyntax: .full)
        ) {
            Text(attr)
        } else {
            Text(message.text)
        }
    }

    var body: some View {
        VStack(alignment: isUser ? .trailing : .leading, spacing: 7) {
            renderedText
                .padding(.horizontal, 14).padding(.vertical, 11)
                .background(isUser ? accent : Color.hodCard)
                .foregroundStyle(isUser ? .white : Color.hodInk)
                .overlay(RoundedRectangle(cornerRadius: 18).stroke(isUser ? .clear : Color.hodInk.opacity(0.10)))
                .clipShape(RoundedRectangle(cornerRadius: 18))
            if !message.places.isEmpty {
                Button { onShowMap(message.places) } label: {
                    Label("Show these on the map", systemImage: "mappin.and.ellipse")
                        .font(.subheadline.weight(.semibold))
                }
                .buttonStyle(.borderedProminent)
                .tint(.hodAegean)
            }
            if !message.sources.isEmpty {
                Text("📓 " + message.sources.joined(separator: " · "))
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(Color.hodAegean)
            }
        }
        .frame(maxWidth: .infinity, alignment: isUser ? .trailing : .leading)
    }
}

struct CandidateCard: View {
    let place: Place
    let onYes: () -> Void
    let onNo: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HodLabel(text: "Is this the place?", color: .hodTerra.opacity(0.8))
            Text(place.name ?? "Unknown").font(.hodDisplay(.title3))
            if let address = place.address, !address.isEmpty {
                Text(address).font(.caption).foregroundStyle(.secondary)
            }
            HStack(spacing: 10) {
                Button("Yes, that's it", action: onYes)
                    .buttonStyle(.borderedProminent).tint(.hodTerra)
                Button("No", action: onNo).buttonStyle(.bordered)
            }
            .padding(.top, 2)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.hodCard, in: RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color.hodTerra.opacity(0.35)))
    }
}

struct PinDot: View {
    let color: Color
    var body: some View {
        Circle()
            .fill(color)
            .frame(width: 18, height: 18)
            .overlay(Circle().stroke(.white, lineWidth: 2.5))
            .shadow(color: .black.opacity(0.28), radius: 2, y: 1)
    }
}

struct HistoryBubble: View {
    let text: String
    let isUser: Bool
    var accent: Color = .hodAegean

    @ViewBuilder
    private var renderedText: some View {
        if let attr = try? AttributedString(markdown: text, options: .init(interpretedSyntax: .full)) {
            Text(attr)
        } else {
            Text(text)
        }
    }

    var body: some View {
        renderedText
            .padding(.horizontal, 14).padding(.vertical, 11)
            .background(isUser ? accent : Color.hodCard)
            .foregroundStyle(isUser ? .white : Color.hodInk)
            .overlay(RoundedRectangle(cornerRadius: 18).stroke(isUser ? .clear : Color.hodInk.opacity(0.10)))
            .clipShape(RoundedRectangle(cornerRadius: 18))
            .frame(maxWidth: .infinity, alignment: isUser ? .trailing : .leading)
    }
}

struct FlowChips: View {
    let items: [(String, Color)]
    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(items.indices, id: \.self) { i in
                    Text(items[i].0)
                        .font(.caption.weight(.semibold))
                        .padding(.horizontal, 11).padding(.vertical, 5)
                        .background(items[i].1.opacity(0.10), in: Capsule())
                        .overlay(Capsule().stroke(items[i].1.opacity(0.30)))
                        .foregroundStyle(items[i].1)
                        .fixedSize()
                }
            }
        }
    }
}
